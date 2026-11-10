import React, { useEffect, useRef, useState } from "react";

const VIDEO_ID = "BPTS64pTbTI";
// If the YouTube player API can't load (blocked network), we can't detect
// the end of the video — unlock Continue after its length instead.
const FALLBACK_UNLOCK_MS = 5 * 60 * 1000;

// One shared promise for the YouTube IFrame API script, which calls the
// global onYouTubeIframeAPIReady when ready.
let ytApiPromise = null;
function loadYouTubeApi() {
  if (window.YT && window.YT.Player) return Promise.resolve(window.YT);
  if (!ytApiPromise) {
    ytApiPromise = new Promise((resolve, reject) => {
      const prev = window.onYouTubeIframeAPIReady;
      window.onYouTubeIframeAPIReady = () => {
        if (prev) prev();
        resolve(window.YT);
      };
      const tag = document.createElement("script");
      tag.src = "https://www.youtube.com/iframe_api";
      tag.onerror = () => { ytApiPromise = null; reject(new Error("YouTube API failed to load")); };
      document.body.appendChild(tag);
    });
  }
  return ytApiPromise;
}

// The demo video shown before the study survey. Continue unlocks once the
// video has played to the end.
export default function DemoVideo({ onDone }) {
  const hostRef = useRef(null);
  const [ended, setEnded] = useState(false);
  const [fallback, setFallback] = useState(false);

  useEffect(() => {
    let player = null;
    let cancelled = false;
    loadYouTubeApi()
      .then((YT) => {
        if (cancelled || !hostRef.current) return;
        // YT.Player replaces its target node with an iframe, so give it a
        // node React doesn't own.
        const target = document.createElement("div");
        hostRef.current.appendChild(target);
        player = new YT.Player(target, {
          videoId: VIDEO_ID,
          playerVars: { rel: 0, modestbranding: 1 },
          events: {
            onStateChange: (e) => {
              if (e.data === YT.PlayerState.ENDED) setEnded(true);
            },
          },
        });
      })
      .catch(() => { if (!cancelled) setFallback(true); });
    return () => {
      cancelled = true;
      if (player && player.destroy) player.destroy();
      if (hostRef.current) hostRef.current.innerHTML = "";
    };
  }, []);

  useEffect(() => {
    if (!fallback) return undefined;
    const t = setTimeout(() => setEnded(true), FALLBACK_UNLOCK_MS);
    return () => clearTimeout(t);
  }, [fallback]);

  return (
    <div className="card">
      <h2>Demo video</h2>
      <p>
        Please watch this short (about 5 minute) demo of how the study works
        before you begin.
      </p>
      <div className="video-frame">
        {fallback ? (
          <iframe
            src={`https://www.youtube.com/embed/${VIDEO_ID}?rel=0`}
            title="Study demo video"
            allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
          />
        ) : (
          <div ref={hostRef} className="video-host" />
        )}
      </div>
      {!ended && (
        <p className="hint">The Continue button unlocks when the video finishes.</p>
      )}
      <button onClick={onDone} disabled={!ended}>Continue</button>
    </div>
  );
}
