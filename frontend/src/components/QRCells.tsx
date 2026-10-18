/** Renders QR modules as grid cells. The parent sets up the 21-column grid. */
export function QRCells({ cells }: { cells: readonly string[] }) {
  return (
    <>
      {cells.map((background, i) => (
        <div key={i} style={{ background, aspectRatio: "1" }} />
      ))}
    </>
  );
}
