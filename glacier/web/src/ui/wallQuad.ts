// Lays a panel exactly onto a wall of the room painting. Each wall panel is a rectangle W x H transformed by a
// projective (perspective) matrix so its four corners land on four points measured on the painting (room.webp,
// 1672 x 941). Text and clicks follow the same transform, so the panel reads as if it is fixed to the wall.
export type Pt = [number, number]
export type Quad = [Pt, Pt, Pt, Pt] // top-left, top-right, bottom-right, bottom-left, in painting pixels

export const PAINT_W = 1672, PAINT_H = 941
// Measured on the approved Limbo image (same room as room.webp).
export const LEFT_WALL: Quad = [[25, 167], [270, 205], [270, 657], [25, 692]]
export const RIGHT_WALL: Quad = [[1384.5, 205], [1647, 165], [1647, 695], [1384.5, 657]]

/** Square-to-quad projective map (Heckbert), returned as a CSS matrix3d for a W x H element with origin 0 0. */
export function quadTransform(w: number, h: number, q: Quad): string {
  const [[x0, y0], [x1, y1], [x2, y2], [x3, y3]] = q
  const dx1 = x1 - x2, dx2 = x3 - x2, dx3 = x0 - x1 + x2 - x3
  const dy1 = y1 - y2, dy2 = y3 - y2, dy3 = y0 - y1 + y2 - y3
  const den = dx1 * dy2 - dx2 * dy1
  const g = den ? (dx3 * dy2 - dx2 * dy3) / den : 0
  const k = den ? (dx1 * dy3 - dx3 * dy1) / den : 0
  const a = x1 - x0 + g * x1, b = x3 - x0 + k * x3, c = x0
  const d = y1 - y0 + g * y1, e = y3 - y0 + k * y3, f = y0
  // H maps element pixels (x, y) to stage pixels: [a/w b/h c; d/w e/h f; g/w k/h 1]
  const m = [a / w, d / w, 0, g / w, b / h, e / h, 0, k / h, 0, 0, 1, 0, c, f, 0, 1]
  return `matrix3d(${m.map(v => +v.toFixed(8)).join(',')})`
}

/** Style for a wall panel on a stage of size sw x sh. The element keeps a natural size close to the wall's. */
export function wallStyle(sw: number, sh: number, q: Quad): { width: number; height: number; transform: string } {
  const sx = sw / PAINT_W, sy = sh / PAINT_H
  const sq = q.map(([x, y]) => [x * sx, y * sy]) as Quad
  const w = Math.round(((sq[1][0] - sq[0][0]) + (sq[2][0] - sq[3][0])) / 2)
  const h = Math.round(((sq[3][1] - sq[0][1]) + (sq[2][1] - sq[1][1])) / 2)
  return { width: w, height: h, transform: quadTransform(w, h, sq) }
}
