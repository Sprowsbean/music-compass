import { useState, useRef } from 'react';
import { Upload, User } from 'lucide-react';
import type { PipelineProgress } from '../hooks/usePipeline';

interface Props {
  onUpload:  (files: File[], name: string) => void;
  loading:   boolean;
  progress:  PipelineProgress | null;
  error:     string;
  disabled?: boolean;
}

export default function UploadZone({ onUpload, loading, progress, error, disabled }: Props) {
  const [name, setName]     = useState('');
  const [nameErr, setNameErr] = useState('');
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const validate = () => {
    if (!name.trim()) { setNameErr('Enter your name first'); return false; }
    setNameErr('');
    return true;
  };

  const submit = (files: FileList | null) => {
    if (!files?.length || !validate()) return;
    onUpload(Array.from(files), name.trim());
  };

  const pct = progress && progress.total > 0
    ? Math.round((progress.current / progress.total) * 100)
    : 0;

  return (
    <div className="space-y-4">

      {/* Name */}
      <div>
        <span className="section-label">
          <User size={10} className="inline mr-1.5" style={{ color: '#00e5ff' }} />
          Your Name
        </span>
        <input
          className="nebula-input"
          style={{ borderColor: nameErr ? '#f87171' : undefined }}
          value={name}
          onChange={e => { setName(e.target.value); if (e.target.value) setNameErr(''); }}
          placeholder="e.g. Alex, Jordan, Norin…"
          disabled={loading || disabled}
        />
        {nameErr && (
          <p style={{ color: '#f87171', fontSize: '0.72rem', marginTop: 4, fontFamily: 'DM Mono' }}>
            {nameErr}
          </p>
        )}
      </div>

      {/* Drop zone */}
      <div
        className={`drop-zone${dragging ? ' drag-active' : ''}`}
        style={{ padding: '40px 24px', textAlign: 'center', opacity: loading ? 0.6 : 1 }}
        onDragEnter={e => { e.preventDefault(); setDragging(true); }}
        onDragLeave={e => { e.preventDefault(); setDragging(false); }}
        onDragOver={e => e.preventDefault()}
        onDrop={e => { e.preventDefault(); setDragging(false); submit(e.dataTransfer.files); }}
        onClick={() => { if (!loading && !disabled && validate()) inputRef.current?.click(); }}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".json"
          multiple
          style={{ display: 'none' }}
          onChange={e => submit(e.target.files)}
          disabled={loading || disabled}
        />
        <Upload
          size={44}
          style={{ margin: '0 auto 14px', color: dragging ? '#00e5ff' : '#3a3860' }}
        />
        <p style={{
          fontFamily: 'Orbitron', fontWeight: 700, fontSize: '0.9rem',
          color: dragging ? '#00e5ff' : '#5a5880', letterSpacing: '0.04em',
        }}>
          {loading ? `SCANNING ${name}'S UNIVERSE…` : 'DROP SPOTIFY JSON HERE'}
        </p>
        <p style={{ color: '#2e2c50', fontSize: '0.72rem', marginTop: 6, fontFamily: 'DM Mono' }}>
          StreamingHistory_music_0.json · or click to browse
        </p>
      </div>

      {/* Progress */}
      {loading && progress && (
        <div className="nebula-card" style={{ padding: 18 }}>
          <div style={{ marginBottom: 10 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
              <span style={{ fontSize: '0.75rem', color: '#5a5880', fontFamily: 'DM Mono' }}>
                {progress.phase}
              </span>
              {progress.total > 0 && (
                <span style={{ fontSize: '0.75rem', color: '#00e5ff', fontFamily: 'Orbitron' }}>
                  {pct}%
                </span>
              )}
            </div>
            {progress.total > 0 && (
              <div style={{ background: 'rgba(255,255,255,0.05)', borderRadius: 3, overflow: 'hidden' }}>
                <div className="progress-bar" style={{ width: `${pct}%` }} />
              </div>
            )}
          </div>
          {progress.total > 0 && (
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
              <span className="badge badge-kaggle">{progress.kaggle} from Kaggle DB</span>
              <span className="badge badge-gemini">{progress.gemini} AI scored</span>
              <span style={{ fontSize: 10, color: '#3a3860', fontFamily: 'DM Mono' }}>
                {progress.current} / {progress.total}
              </span>
            </div>
          )}
        </div>
      )}

      {/* Error */}
      {error && (
        <div style={{
          background: 'rgba(248,113,113,0.08)',
          border: '1px solid rgba(248,113,113,0.3)',
          borderRadius: 8, padding: '10px 14px',
        }}>
          <p style={{ color: '#fca5a5', fontSize: '0.78rem', fontFamily: 'DM Mono' }}>{error}</p>
        </div>
      )}
    </div>
  );
}
