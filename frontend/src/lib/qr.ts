/**
 * Tiny QR Code encoder: version 1 (21×21), byte mode, error-correction level L,
 * mask pattern 0. Enough for short codes like "BILLO-4821" (≤17 bytes).
 * Ported 1:1 from the original design's inline script.
 */
const N = 21;

/** GF(256) multiply with the QR polynomial 0x11D. */
function gfMul(x: number, y: number): number {
  let z = 0;
  for (let i = 7; i >= 0; i--) {
    z = (z << 1) ^ ((z >>> 7) * 0x11d);
    z ^= ((y >>> i) & 1) * x;
  }
  return z & 255;
}

/** Returns a flat 21×21 boolean matrix (row-major); true = dark module. */
export function qrMatrix(text: string): boolean[] {
  const bytes = Array.from(new TextEncoder().encode(text));
  const bits: number[] = [];
  const push = (v: number, n: number) => {
    for (let i = n - 1; i >= 0; i--) bits.push((v >>> i) & 1);
  };

  // Data: mode indicator, length, payload, terminator, padding.
  push(4, 4);
  push(bytes.length, 8);
  bytes.forEach((b) => push(b, 8));
  push(0, Math.min(4, 152 - bits.length));
  while (bits.length % 8) bits.push(0);

  const data: number[] = [];
  for (let i = 0; i < bits.length; i += 8) {
    let v = 0;
    for (let j = 0; j < 8; j++) v = (v << 1) | bits[i + j];
    data.push(v);
  }
  for (let p = 0xec; data.length < 19; p ^= 0xec ^ 0x11) data.push(p);

  // Reed–Solomon error correction (7 codewords).
  const deg = 7;
  const div = new Array<number>(deg).fill(0);
  div[deg - 1] = 1;
  let root = 1;
  for (let i = 0; i < deg; i++) {
    for (let j = 0; j < deg; j++) {
      div[j] = gfMul(div[j], root);
      if (j + 1 < deg) div[j] ^= div[j + 1];
    }
    root = gfMul(root, 2);
  }
  const rem = new Array<number>(deg).fill(0);
  data.forEach((b) => {
    const f = b ^ (rem.shift() as number);
    rem.push(0);
    div.forEach((c, i) => (rem[i] ^= gfMul(c, f)));
  });
  const codewords = data.concat(rem);

  // Matrix with function patterns.
  const m = [...Array(N)].map(() => Array<boolean>(N).fill(false));
  const fn = [...Array(N)].map(() => Array<boolean>(N).fill(false));
  const set = (x: number, y: number, d: boolean) => {
    m[y][x] = d;
    fn[y][x] = true;
  };

  for (let i = 0; i < N; i++) {
    set(6, i, i % 2 === 0);
    set(i, 6, i % 2 === 0);
  }
  for (const [cx, cy] of [
    [3, 3],
    [N - 4, 3],
    [3, N - 4],
  ]) {
    for (let dy = -4; dy <= 4; dy++)
      for (let dx = -4; dx <= 4; dx++) {
        const x = cx + dx;
        const y = cy + dy;
        if (x >= 0 && x < N && y >= 0 && y < N) {
          const d = Math.max(Math.abs(dx), Math.abs(dy));
          set(x, y, d !== 2 && d !== 4);
        }
      }
  }

  // Format information (level L, mask 0).
  const fd = (1 << 3) | 0;
  let r = fd;
  for (let i = 0; i < 10; i++) r = (r << 1) ^ ((r >>> 9) * 0x537);
  const fb = ((fd << 10) | r) ^ 0x5412;
  const g = (i: number) => ((fb >>> i) & 1) === 1;
  for (let i = 0; i <= 5; i++) set(8, i, g(i));
  set(8, 7, g(6));
  set(8, 8, g(7));
  set(7, 8, g(8));
  for (let i = 9; i < 15; i++) set(14 - i, 8, g(i));
  for (let i = 0; i < 8; i++) set(N - 1 - i, 8, g(i));
  for (let i = 8; i < 15; i++) set(8, N - 15 + i, g(i));
  set(8, N - 8, true);

  // Zig-zag data placement.
  let k = 0;
  for (let right = N - 1; right >= 1; right -= 2) {
    if (right === 6) right = 5;
    for (let v = 0; v < N; v++)
      for (let j = 0; j < 2; j++) {
        const x = right - j;
        const up = ((right + 1) & 2) === 0;
        const y = up ? N - 1 - v : v;
        if (!fn[y][x] && k < codewords.length * 8) {
          m[y][x] = ((codewords[k >>> 3] >>> (7 - (k & 7))) & 1) === 1;
          k++;
        }
      }
  }

  // Mask 0: (x + y) % 2 === 0.
  for (let y = 0; y < N; y++) for (let x = 0; x < N; x++) if (!fn[y][x] && (x + y) % 2 === 0) m[y][x] = !m[y][x];

  return m.flat();
}

/** QR modules as CSS colours, ready for <QRCells />. */
export function makeQR(text: string, dark = "var(--color-text)", light = "transparent"): string[] {
  return qrMatrix(text).map((d) => (d ? dark : light));
}
