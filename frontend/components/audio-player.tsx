"use client";

import { useEffect, useRef, useState, useMemo } from "react";

interface AudioPlayerProps {
  url: string;
  trackId: string; 
}

// Simple deterministic pseudo-random number generator for barcode aesthetic based on string 
function seededRandom(seed: string) {
  let hash = 0;
  for (let i = 0; i < seed.length; i++) {
    hash = Math.imul(31, hash) + seed.charCodeAt(i) | 0;
  }
  return () => {
    hash = Math.imul(741103597, hash) + 1950346763 | 0;
    return (hash >>> 0) / 4294967296;
  };
}

let activeTrackId: string | null = null;

export default function AudioPlayer({ url, trackId }: AudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const waveformRef = useRef<HTMLDivElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0); 
  const [isDragging, setIsDragging] = useState(false);
  const [volume, setVolume] = useState(0.20); 
  const [duration, setDuration] = useState(0);
  const [showVolume, setShowVolume] = useState(false);
  
  // Generate 42 barcode heights deterministically from the song's track id so it always looks identical for that song
  const bars = useMemo(() => {
    const rng = seededRandom(trackId);
    return Array.from({ length: 42 }, () => rng() * 0.7 + 0.3); // sizes from 30% to 100% height
  }, [trackId]);

  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.volume = volume;
    }
  }, [volume]); 

  // Handle Spacebar to play/pause globally for active track
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't intercept if user is typing in a form field
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      
      if (e.code === "Space") {
        if (activeTrackId === trackId && audioRef.current) {
          e.preventDefault(); // Stop page scrolling
          if (isPlaying) {
            audioRef.current.pause();
          } else {
            // Re-pause all other media simply to be safe
            const allAudios = document.querySelectorAll('audio');
            allAudios.forEach(a => { if (a !== audioRef.current) a.pause() });
            void audioRef.current.play().catch(() => {});
          }
        }
      }
    };
    
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [trackId, isPlaying]);

  const togglePlay = () => {
    if (!audioRef.current) return;
    if (isPlaying) {
      audioRef.current.pause();
    } else {
      activeTrackId = trackId;
      // Pause any other playing audio on the page
      const allAudios = document.querySelectorAll('audio');
      allAudios.forEach(a => { if (a !== audioRef.current) a.pause() });
      
      void audioRef.current.play().catch(() => setIsPlaying(false));
    }
  };

  const handleTimeUpdate = () => {
    if (!audioRef.current || !duration || isDragging) return;
    setProgress(audioRef.current.currentTime / duration);
  };

  const handleLoadedMetadata = () => {
    if (audioRef.current) {
      setDuration(audioRef.current.duration || 30);
    }
  };

  const handleEnded = () => {
    setIsPlaying(false);
    setProgress(0);
    if (audioRef.current) audioRef.current.currentTime = 0;
  };

  const handlePause = () => setIsPlaying(false);
  const handlePlay = () => {
    setIsPlaying(true);
    activeTrackId = trackId;
  };

  const handlePointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    setIsDragging(true);
    e.currentTarget.setPointerCapture(e.pointerId);
    
    if (waveformRef.current) {
      const rect = waveformRef.current.getBoundingClientRect();
      const ratio = (e.clientX - rect.left) / rect.width;
      const boundedRatio = Math.max(0, Math.min(1, ratio));
      setProgress(boundedRatio);
    }
  };

  const handlePointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!isDragging || !waveformRef.current) return;
    
    const rect = waveformRef.current.getBoundingClientRect();
    const ratio = (e.clientX - rect.left) / rect.width;
    const boundedRatio = Math.max(0, Math.min(1, ratio));
    setProgress(boundedRatio);
  };

  const handlePointerUp = (e: React.PointerEvent<HTMLDivElement>) => {
    setIsDragging(false);
    e.currentTarget.releasePointerCapture(e.pointerId);
    
    if (audioRef.current && duration > 0) {
      const rect = waveformRef.current.getBoundingClientRect();
      const ratio = (e.clientX - rect.left) / rect.width;
      const boundedRatio = Math.max(0, Math.min(1, ratio));
      
      setProgress(boundedRatio);
      audioRef.current.currentTime = boundedRatio * duration;
    }
  };

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newVol = parseFloat(e.target.value);
    setVolume(newVol);
    if (audioRef.current) {
      audioRef.current.volume = newVol;
    }
  };

  return (
    <div className="custom-audio-player">
      <audio 
        ref={audioRef} 
        src={url} 
        preload="none"
        onTimeUpdate={handleTimeUpdate}
        onLoadedMetadata={handleLoadedMetadata}
        onEnded={handleEnded}
        onPause={handlePause}
        onPlay={handlePlay}
      />
      
      <button className="play-btn" onClick={togglePlay} aria-label={isPlaying ? "Pause" : "Play"}>
        {isPlaying ? (
          <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor">
            <rect x="6" y="4" width="4" height="16" />
            <rect x="14" y="4" width="4" height="16" />
          </svg>
        ) : (
          <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor">
            <polygon points="5 3 19 12 5 21 5 3" />
          </svg>
        )}
      </button>

      <div 
        className="barcode-waveform" 
        ref={waveformRef}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
      >
        {bars.map((height, i) => {
          const ratio = i / bars.length;
          const isActive = ratio <= progress;
          return (
             <div 
               key={i} 
               className={`barcode-bar ${isActive ? 'active' : ''} ${isDragging ? 'dragging' : ''}`} 
               style={{ height: `${height * 100}%` }}
             />
          );
        })}
      </div>

      <div 
        className="volume-container" 
        onMouseEnter={() => setShowVolume(true)} 
        onMouseLeave={() => setShowVolume(false)}
      >
        <button className="vol-btn" aria-label="Volume">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            {volume === 0 ? (
              <><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><line x1="23" y1="9" x2="17" y2="15"></line><line x1="17" y1="9" x2="23" y2="15"></line></>
            ) : volume < 0.5 ? (
              <><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path></>
            ) : (
               <><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path></>
            )}
          </svg>
        </button>
        
        {showVolume && (
          <div className="volume-popup">
            <div className="volume-slider-wrap">
              <input 
                type="range" 
                min="0" 
                max="1" 
                step="0.01" 
                value={volume} 
                onChange={handleVolumeChange} 
                className="vol-slider"
                style={{ 
                  background: `linear-gradient(to right, var(--text) ${volume * 100}%, #e0e0dc ${volume * 100}%)` 
                }}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}