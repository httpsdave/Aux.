"use client";

import { useState } from "react";
import Image from "next/image";

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
          <audio controls preload="none" src={song.preview_url}>
            Your browser does not support the audio element.
          </audio>
        ) : (
          <span className="preview-missing" aria-label="Preview unavailable">
            Preview unavailable
          </span>
        )}
      </div>

      <div className="actions">
        <button type="button" onClick={() => setExpanded((value) => !value)} className="details-btn">
          {expanded ? "Hide details" : "More details"}
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
