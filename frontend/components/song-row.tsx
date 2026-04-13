"use client";

import { useState } from "react";
import Image from "next/image";

import AudioPlayer from "@/components/audio-player";
import { SongEntry } from "@/lib/types";

interface SongRowProps {
  song: SongEntry;
}

export default function SongRow({ song }: SongRowProps) {
  const [expanded, setExpanded] = useState(false);
  const generatedCover = `https://api.dicebear.com/9.x/shapes/svg?seed=${encodeURIComponent(`${song.title}-${song.artist}`)}`;
  const coverSrc = song.image_url || generatedCover;
  const movementSymbol =
    song.last_week_position == null
      ? "-"
      : song.last_week_position > song.rank
      ? "↑"
      : song.last_week_position < song.rank
      ? "↓"
      : "→";
  const movementClass =
    movementSymbol === "↑" ? "movement up" : movementSymbol === "↓" ? "movement down" : "movement";

  return (
    <article className={`song-row${expanded ? " expanded" : ""}`}>
      <div className="rank">{song.rank}</div>
      <div className="cover-wrap">
        <Image
          src={coverSrc}
          alt={`${song.title} album art`}
          width={90}
          height={90}
          className="cover"
          unoptimized
        />
      </div>

      <div className="meta">
        <div className={movementClass}>{movementSymbol}</div>
        <div>
          <h3>{song.title}</h3>
          <p>{song.artist}</p>
          {song.album ? <p className="album">{song.album}</p> : null}
        </div>
      </div>

      <dl className="stats">
        <div>
          <dt>LW</dt>
          <dd>{song.last_week_position ?? "-"}</dd>
        </div>
        <div>
          <dt>Peak</dt>
          <dd>{song.peak_position ?? "-"}</dd>
        </div>
        <div>
          <dt>Weeks</dt>
          <dd>{song.weeks_on_chart ?? "-"}</dd>
        </div>
      </dl>

      <div className="preview">
        {song.preview_url ? (
          <AudioPlayer url={song.preview_url} trackId={`${song.title}-${song.artist}`} />
        ) : (
          <span className="preview-missing" aria-label="Preview unavailable">
            Preview unavailable
          </span>
        )}
      </div>

      <div className="actions">
        <button 
          type="button" 
          onClick={() => setExpanded((value) => !value)} 
          className="details-btn icon-btn"
          title={expanded ? "Hide details" : "More details"}
          aria-expanded={expanded}
          aria-label={expanded ? "Hide details" : "More details"}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            {expanded ? <polyline points="18 15 12 9 6 15"></polyline> : <polyline points="6 9 12 15 18 9"></polyline>}
          </svg>
        </button>
      </div>

      {expanded ? (
        <div className="details-panel">
          <p>
            <strong>Song:</strong> {song.title}
          </p>
          <p>
            <strong>Artist:</strong> {song.artist}
          </p>
          <p>
            <strong>Album:</strong> {song.album || "Unknown"}
          </p>
          <p>
            <strong>Preview:</strong> {song.preview_url ? "Available" : "Not available"}
          </p>
        </div>
      ) : null}
    </article>
  );
}
