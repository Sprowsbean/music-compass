interface Props {
  data:      any;   // AstrologyResult from API
  userColor: string;
}

const ELEMENT_COLORS: Record<string, string> = {
  Fire: '#f97316', Water: '#00e5ff', Earth: '#34d399',
  Air: '#e8e6ff', Void: '#a78bfa', Plasma: '#f472b6',
};

export default function AstrologyCard({ data, userColor }: Props) {
  const reading = data?.reading;
  if (!reading) return null;

  const elColor = ELEMENT_COLORS[reading.element] ?? userColor;

  return (
    <div className="fade-up" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Header row */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
        <div>
          <div style={{
            fontFamily: 'Orbitron', fontWeight: 900, fontSize: 22,
            color: userColor, letterSpacing: '0.03em', marginBottom: 4,
          }}>
            {reading.archetype}
          </div>
          <div style={{
            fontFamily: 'DM Mono', fontSize: 13, color: '#8b87c0',
            fontStyle: 'italic', maxWidth: 480,
          }}>
            "{reading.headline}"
          </div>
        </div>

        <div style={{
          textAlign: 'center', padding: '12px 18px', borderRadius: 10,
          background: elColor + '12', border: `1px solid ${elColor}35`,
        }}>
          <div style={{ fontSize: 9, letterSpacing: '0.15em', color: '#4a4870', marginBottom: 4, fontFamily: 'Orbitron' }}>
            ELEMENT
          </div>
          <div style={{ fontFamily: 'Orbitron', fontWeight: 800, fontSize: 16, color: elColor }}>
            {reading.element}
          </div>
          <div style={{ fontSize: 9, color: '#3a3860', marginTop: 2, fontFamily: 'DM Mono' }}>
            {reading.hz}
          </div>
        </div>
      </div>

      {/* Reading body */}
      <div style={{
        padding: '16px 20px',
        background: 'rgba(79,70,229,0.04)',
        border: `1px solid rgba(79,70,229,0.2)`,
        borderLeft: `4px solid ${userColor}`,
        borderRadius: '0 10px 10px 0',
      }}>
        <p style={{
          fontFamily: 'DM Mono', fontSize: 13, color: '#9b98c8',
          lineHeight: 1.95, margin: 0,
        }}>
          {reading.reading}
        </p>
      </div>

      {/* Data summary */}
      {data.centroid && (
        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
          {[
            ['Centroid Energy',  data.centroid.energy.toFixed(3),  '#00e5ff'],
            ['Centroid Valence', data.centroid.valence.toFixed(3), '#f472b6'],
            ['Quadrant',        data.quadrant,                      '#fbbf24'],
          ].map(([label, val, col]) => (
            <div key={label} style={{
              flex: 1, minWidth: 120, textAlign: 'center',
              padding: '10px 14px', borderRadius: 8,
              background: `${col}0d`, border: `1px solid ${col}25`,
            }}>
              <div style={{ fontSize: 9, color: '#4a4870', fontFamily: 'Orbitron', letterSpacing: '0.1em', marginBottom: 3 }}>{label}</div>
              <div style={{ fontSize: 13, color: col, fontFamily: 'Orbitron', fontWeight: 700 }}>{val}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
