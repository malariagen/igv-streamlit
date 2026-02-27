"""
igv-streamlit
=============

A custom Streamlit component for embedding the igv.js genome browser into Streamlit apps.

Supports both local files (served via a built-in CORS HTTP server) and remote URLs.

Basic usage
-----------
>>> import igv_streamlit as st_igv
>>>
>>> st_igv.browser(
...     genome="hg38",
...     locus="chr1:1,000,000-1,100,000",
...     tracks=[
...         {
...             "name": "My BAM",
...             "url": "https://...",
...             "indexURL": "https://...",
...             "type": "alignment",
...         }
...     ],
... )

Local file usage
----------------
Use ``path`` / ``indexPath`` / ``fastaPath`` instead of ``url`` / ``indexURL`` / ``fastaURL``
when pointing to files on the local filesystem:

>>> st_igv.browser(
...     reference={
...         "fastaPath": "/data/ref.fasta",
...         "cytobandPath": "/data/ref.cytoband",
...     },
...     tracks=[
...         {
...             "name": "Local CRAM",
...             "path":      "/data/sample.cram",
...             "indexPath": "/data/sample.cram.crai",
...             "type": "alignment",
...         }
...     ],
... )
"""

from __future__ import annotations

import copy
import os
import inspect
from typing import Any

import streamlit as st

from .server import register_file

# ── igv.js CDN (pinned to a stable 3.x release) ──────────────────────────────
_IGV_JS_URL = "https://cdn.jsdelivr.net/npm/igv@3.1.2/dist/igv.min.js"

# ── path → url property mapping (mirrors igv-notebook) ───────────────────────
_PATH_TO_URL: dict[str, str] = {
    "path":        "url",
    "indexPath":   "indexURL",
    "fastaPath":   "fastaURL",
    "cytobandPath":"cytobandURL",
    "aliasPath":   "aliasURL",
}

# ── JavaScript for the v2 component ──────────────────────────────────────────
_JS = r"""
export default function(component) {
    const { data, parentElement, setStateValue } = component;
    if (!data || !data.config) return;

    const config     = data.config;
    const configJson = JSON.stringify(config);
    const height     = data.height || 500;

    if (!parentElement._igvScaffold) {

        const outerContainer = document.createElement('div');
        outerContainer.className = 'sigv-outer';

        const toolbar = document.createElement('div');
        toolbar.className = 'sigv-toolbar';

        const igvWrapper = document.createElement('div');
        igvWrapper.className = 'sigv-browser';

        const fsBtn = document.createElement('button');
        fsBtn.className = 'sigv-btn';
        fsBtn.title = 'Enter full screen';
        fsBtn.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
                 stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="15 3 21 3 21 9"/>
              <polyline points="9 21 3 21 3 15"/>
              <line x1="21" y1="3" x2="14" y2="10"/>
              <line x1="3" y1="21" x2="10" y2="14"/>
            </svg>
            Full screen`;

        const exitBtn = document.createElement('button');
        exitBtn.className = 'sigv-btn';
        exitBtn.title = 'Exit full screen  (Esc)';
        exitBtn.style.display = 'none';
        exitBtn.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
                 stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="4 14 10 14 10 20"/>
              <polyline points="20 10 14 10 14 4"/>
              <line x1="10" y1="14" x2="3" y2="21"/>
              <line x1="21" y1="3" x2="14" y2="10"/>
            </svg>
            Exit full screen`;

        toolbar.appendChild(fsBtn);
        toolbar.appendChild(exitBtn);
        outerContainer.appendChild(toolbar);
        outerContainer.appendChild(igvWrapper);
        parentElement.appendChild(outerContainer);

        // Single source of truth for fullscreen state — stored on the scaffold
        // so external code can inspect it, and used directly in this closure.
        const scaffold = {
            outerContainer, igvWrapper, toolbar, fsBtn, exitBtn,
            isFullscreen: false,
        };
        parentElement._igvScaffold = scaffold;

        let _fsOverlay   = null;
        let _origParent  = null;
        let _origSibling = null;

        const triggerIgvResize = () => {
            if (!igvWrapper._igvBrowser) return;
            window.dispatchEvent(new Event('resize'));
        };

        // ── Fullscreen enter / exit ───────────────────────────────────────────
        //
        // Lesson learned through debugging: this JS runs directly in the page
        // (frame depth = 0), so position:fixed on document.body covers the full
        // viewport correctly.  The tricky part is that Streamlit's st.dialog
        // injects stylesheets that override class-based CSS — even !important —
        // changing display:flex to block and inflating inherited font sizes.
        // Solution: stamp every layout-critical value as inline styles during
        // fullscreen, then clear them on exit to restore the CSS classes.

        // Shared inline style for the exit button.  Fully specified so that
        // inherited font-size / padding from the dialog can't inflate it.
        // Note: :hover and transition can't be set inline, so we add a one-off
        // <style> rule scoped to a data attribute instead (see below).
        const _BTN_INLINE =
            'display:flex;align-items:center;gap:6px;' +
            'padding:5px 12px;height:30px;box-sizing:border-box;' +
            'font-size:13px;font-family:inherit;font-weight:500;line-height:1.2;' +
            'border:1px solid rgba(128,128,128,0.35);border-radius:6px;' +
            'background:rgba(255,255,255,0.88);backdrop-filter:blur(4px);' +
            'color:#333;cursor:pointer;white-space:nowrap;' +
            'box-shadow:0 1px 4px rgba(0,0,0,0.12);' +
            'transition:background 0.15s,box-shadow 0.15s,transform 0.1s;';

        const enterFullscreen = () => {
            if (scaffold.isFullscreen) return;
            scaffold.isFullscreen = true;

            const pageBg = getComputedStyle(document.body).backgroundColor || '#ffffff';
            _origParent  = outerContainer.parentNode;
            _origSibling = outerContainer.nextSibling;

            // Full-viewport backdrop
            _fsOverlay = document.createElement('div');
            _fsOverlay.style.cssText =
                'position:fixed;top:0;left:0;width:100%;height:100%;' +
                `background:${pageBg};z-index:2147483646;margin:0;padding:0;box-sizing:border-box;`;
            document.body.appendChild(_fsOverlay);

            // Move container into overlay; stamp layout inline to beat dialog CSS
            _fsOverlay.appendChild(outerContainer);
            outerContainer.style.cssText =
                'position:fixed;top:0;left:0;width:100%;height:100%;' +
                'z-index:2147483647;margin:0;padding:0;box-sizing:border-box;' +
                'display:flex;flex-direction:column;';
            outerContainer.style.setProperty('--sigv-height', '100vh');

            toolbar.style.cssText =
                'display:flex;flex-direction:row;align-items:center;' +
                'justify-content:flex-end;flex-shrink:0;width:100%;' +
                'height:40px;padding:0 8px;box-sizing:border-box;' +
                'border-bottom:1px solid rgba(128,128,128,0.15);';

            exitBtn.style.cssText = _BTN_INLINE;

            fsBtn.style.display   = 'none';
            // display is already included in _BTN_INLINE, no need to set again
            requestAnimationFrame(triggerIgvResize);
        };

        const exitFullscreen = () => {
            if (!scaffold.isFullscreen) return;
            scaffold.isFullscreen = false;

            // Restore DOM position
            if (_origParent) {
                _origParent.insertBefore(outerContainer, _origSibling || null);
            }

            // Clear inline overrides — CSS classes take over again
            outerContainer.style.cssText = '';
            outerContainer.style.setProperty('--sigv-height', height + 'px');
            toolbar.style.cssText  = '';
            exitBtn.style.cssText  = '';

            // Remove backdrop
            if (_fsOverlay && _fsOverlay.parentNode) {
                _fsOverlay.parentNode.removeChild(_fsOverlay);
            }
            _fsOverlay   = null;
            _origParent  = null;
            _origSibling = null;

            fsBtn.style.display   = 'flex';
            exitBtn.style.display = 'none';
            requestAnimationFrame(triggerIgvResize);
        };

        fsBtn.addEventListener('click',  enterFullscreen);
        exitBtn.addEventListener('click', exitFullscreen);

        const onKeyDown = (e) => {
            if (e.key === 'Escape' && scaffold.isFullscreen) exitFullscreen();
        };
        document.addEventListener('keydown', onKeyDown);

        scaffold._cleanup = () => {
            document.removeEventListener('keydown', onKeyDown);
            if (scaffold.isFullscreen) exitFullscreen();
        };
    }

    const { outerContainer, igvWrapper } = parentElement._igvScaffold;

    if (!parentElement._igvScaffold.isFullscreen) {
        outerContainer.style.setProperty('--sigv-height', height + 'px');
    }

    // ── IGV browser lifecycle ─────────────────────────────────────────────────

    const destroyBrowser = () => {
        const browser = igvWrapper._igvBrowser;
        if (browser && window.igv) {
            try { window.igv.removeBrowser(browser); } catch (_) {}
            igvWrapper._igvBrowser    = null;
            igvWrapper._igvConfigJson = null;
            igvWrapper.innerHTML      = '';
        }
    };

    const createBrowser = () => {
        destroyBrowser();
        window.igv.createBrowser(igvWrapper, config)
            .then(browser => {
                igvWrapper._igvBrowser    = browser;
                igvWrapper._igvConfigJson = configJson;
                if (data.trackLocus) {
                    let _locusTid  = null;
                    let _lastLocus = null;
                    browser.on('locuschange', (_frames, label) => {
                        if (_locusTid) clearTimeout(_locusTid);
                        _locusTid = setTimeout(() => {
                            _locusTid = null;
                            if (label === _lastLocus) return;
                            _lastLocus = label;
                            setStateValue('locus', label);
                        }, 300);
                    });
                }
            })
            .catch(err => {
                igvWrapper.innerHTML =
                    `<div style="color:red;padding:12px;font-family:monospace">
                        IGV error: ${err.message || err}
                    </div>`;
                console.error('IGV error:', err);
            });
    };

    const launchIfNeeded = () => {
        if (igvWrapper._igvConfigJson === configJson) return;
        createBrowser();
    };

    // ── igv.js loading — namespaced flag to avoid collisions between multiple
    //    browser instances on the same page (plain window._igvScriptLoading
    //    would be shared and could cause a race).
    if (window.igv) {
        launchIfNeeded();
    } else if (window.__igvScriptPromise) {
        window.__igvScriptPromise.then(launchIfNeeded);
    } else {
        window.__igvScriptPromise = new Promise((resolve, reject) => {
            const s = document.createElement('script');
            s.src     = data.igvJsUrl;
            s.onload  = resolve;
            s.onerror = reject;
            document.head.appendChild(s);
        });
        window.__igvScriptPromise
            .then(launchIfNeeded)
            .catch(() => {
                igvWrapper.innerHTML =
                    `<div style="color:red;padding:12px;font-family:monospace">
                        Failed to load igv.js from ${data.igvJsUrl}
                    </div>`;
            });
    }

    return () => {
        destroyBrowser();
        if (parentElement._igvScaffold?._cleanup) {
            parentElement._igvScaffold._cleanup();
        }
    };
}
"""

# ── CSS ───────────────────────────────────────────────────────────────────────
_CSS = """
.sigv-outer {
    display:        flex;
    flex-direction: column;
    width:          100%;
    height:         var(--sigv-height, 500px);
    background:     var(--st-background-color, #fff);
    box-sizing:     border-box;
}
.sigv-toolbar {
    display:         flex;
    align-items:     center;
    justify-content: flex-end;
    flex-shrink:     0;
    height:          40px;
    padding:         0 8px;
    border-bottom:   1px solid rgba(128,128,128,0.15);
    background:      var(--st-background-color, #fff);
    box-sizing:      border-box;
}
.sigv-browser {
    flex:       1;
    width:      100%;
    overflow:   hidden;
    min-height: 0;
}
.sigv-btn {
    display:         flex;
    align-items:     center;
    gap:             6px;
    padding:         5px 12px;
    border:          1px solid rgba(128,128,128,0.35);
    border-radius:   6px;
    background:      rgba(255,255,255,0.88);
    backdrop-filter: blur(4px);
    color:           #333;
    font-size:       13px;
    font-family:     inherit;
    font-weight:     500;
    cursor:          pointer;
    transition:      background 0.15s, box-shadow 0.15s, transform 0.1s;
    box-shadow:      0 1px 4px rgba(0,0,0,0.12);
    white-space:     nowrap;
    box-sizing:      border-box;
}
.sigv-btn svg {
    width:       15px;
    height:      15px;
    flex-shrink: 0;
}
.sigv-btn:hover {
    background:  rgba(255,255,255,0.97);
    box-shadow:  0 2px 8px rgba(0,0,0,0.18);
    transform:   translateY(-1px);
}
.sigv-btn:active {
    transform:  translateY(0);
    box-shadow: 0 1px 3px rgba(0,0,0,0.12);
}
.igv-navbar { box-sizing: border-box !important; }
"""

# ── Register & cache the v2 component (done once per Python session) ──────────
_igv_component = st.components.v2.component(
    "igv_streamlit.browser",
    js=_JS,
    css=_CSS,
)


# ── helpers ───────────────────────────────────────────────────────────────────

def _resolve_local_paths(obj: Any) -> Any:
    """
    Recursively walk a config dict/list and replace any ``path``-style
    properties with ``url``-style ones pointing to the local file server.
    """
    if isinstance(obj, list):
        return [_resolve_local_paths(item) for item in obj]

    if isinstance(obj, dict):
        resolved: dict[str, Any] = {}
        for key, value in obj.items():
            if key in _PATH_TO_URL and isinstance(value, str):
                url_key = _PATH_TO_URL[key]
                resolved[url_key] = register_file(value)
            else:
                resolved[key] = _resolve_local_paths(value)
        return resolved

    return obj


def _build_igv_config(
    genome: str | dict | None,
    reference: dict | None,
    locus: str | None,
    tracks: list[dict] | None,
    extra: dict,
) -> dict:
    config: dict[str, Any] = {}

    if genome and isinstance(genome, str):
        config["genome"] = genome
    elif genome and isinstance(genome, dict):
        config["reference"] = _resolve_local_paths(copy.deepcopy(genome))

    if reference:
        config["reference"] = _resolve_local_paths(copy.deepcopy(reference))

    if locus:
        config["locus"] = locus

    if tracks:
        config["tracks"] = _resolve_local_paths(copy.deepcopy(tracks))

    config.update(extra)
    return config


# ── Public API ────────────────────────────────────────────────────────────────
def resolve_path(path: str) -> str:
    """
    Resolve a path relative to the calling script's directory.

    Paths passed via ``path`` / ``indexPath`` / ``fastaPath`` etc. are resolved
    relative to Python's current working directory (i.e. where you launched
    Streamlit from). If your data files live next to your script and you want
    paths relative to the script instead, use :func:`resolve_path`:

    >>> st_igv.browser(
    ...     reference={
    ...         "fastaPath": st_igv.resolve_path("data/ref.fasta"),
    ...     },
    ...     tracks=[{
    ...         "name": "My CRAM",
    ...         "path": st_igv.resolve_path("data/sample.cram"),
    ...         "indexPath": st_igv.resolve_path("data/sample.cram.crai"),
    ...         "type": "alignment",
    ...     }],
    ... )

    Absolute paths always work without ``resolve_path``.
    """
    if os.path.isabs(path):
        return path
    caller_dir = os.path.dirname(os.path.abspath(inspect.stack()[1].filename))
    return os.path.join(caller_dir, path)


def browser(
    genome: str | dict | None = None,
    *,
    reference: dict | None = None,
    locus: str | None = None,
    tracks: list[dict] | None = None,
    height: int = 500,
    key: str | None = None,
    on_locus_change=None,
    **kwargs,
):
    """
    Render an IGV genome browser inside a Streamlit app.

    Parameters
    ----------
    genome : str or dict, optional
        A built-in genome ID (e.g. ``"hg38"``, ``"mm10"``), or a reference
        config dict with ``fastaURL``/``fastaPath`` keys.
    reference : dict, optional
        Explicit IGV reference object (use instead of ``genome`` for custom
        references). Supports ``fastaPath`` for local FASTA files.
    locus : str, optional
        Initial genomic locus, e.g. ``"chr1:1,000,000-1,100,000"`` or a gene
        name like ``"BRCA1"``.
    tracks : list of dict, optional
        List of IGV track configuration objects. Use ``path``/``indexPath``
        for local files; ``url``/``indexURL`` for remote files.
    height : int, optional
        Height of the browser in pixels (default: 500).
    key : str, optional
        Streamlit component key for uniqueness when using multiple browsers.
    on_locus_change : callable, optional
        Callback invoked when the user navigates to a new locus.
    **kwargs
        Any additional IGV browser config options passed through directly.

    Returns
    -------
    result
        A Streamlit component result. Access ``result.locus`` for the current
        genomic position (updated on navigation).
    """
    config = _build_igv_config(genome, reference, locus, tracks, kwargs)

    callbacks = {}
    if on_locus_change is not None:
        callbacks["on_locus_change"] = on_locus_change

    result = _igv_component(
        data={"config": config, "height": height, "igvJsUrl": _IGV_JS_URL,
              "trackLocus": on_locus_change is not None},
        key=key,
        **callbacks,
    )
    return result


__all__ = ["browser", "resolve_path"]