/* Display geometry only: never computes route order, cost, or ETA. */
(function () {
  "use strict";
  function decodePolyline(encoded) {
    const coords = []; let offset = 0, lat = 0, lon = 0;
    function delta() {
      let value = 0, shift = 0, byte;
      do {
        if (offset >= encoded.length || shift > 30) throw new Error("Invalid road geometry");
        byte = encoded.charCodeAt(offset++) - 63; value |= (byte & 31) << shift; shift += 5;
      } while (byte >= 32);
      return (value & 1) ? ~(value >> 1) : value >> 1;
    }
    while (offset < encoded.length) { lat += delta(); lon += delta(); coords.push({ lat: lat / 100000, lon: lon / 100000 }); }
    return coords;
  }

  function buildTrack(paths) {
    let start = 0;
    return paths.map((points) => {
      if (!points.length) throw new Error("A playback leg needs geometry");
      const lengths = [0];
      for (let i = 1; i < points.length; i++) lengths.push(lengths[i - 1] + Math.hypot(points[i][0] - points[i - 1][0], points[i][1] - points[i - 1][1]));
      const path = { points, lengths, total: lengths.at(-1), start };
      start += path.total;
      return path;
    });
  }

  function position(track, progress) {
    if (!track.length) throw new Error("No route to play");
    const clamped = Math.max(0, Math.min(track.length, progress));
    const leg = Math.min(track.length - 1, Math.floor(clamped)), path = track[leg];
    const distance = path.total * (clamped === track.length ? 1 : clamped - leg);
    let low = 1, high = path.points.length - 1;
    while (low < high) { const middle = Math.floor((low + high) / 2); if (path.lengths[middle] < distance) low = middle + 1; else high = middle; }
    const end = path.points[low] || path.points[0], start = path.points[Math.max(0, low - 1)];
    const span = (path.lengths[low] || 0) - path.lengths[Math.max(0, low - 1)];
    const fraction = span ? (distance - path.lengths[low - 1]) / span : 0;
    return { x: start[0] + (end[0] - start[0]) * fraction, y: start[1] + (end[1] - start[1]) * fraction,
      angle: Math.atan2(end[1] - start[1], end[0] - start[0]) * 180 / Math.PI, leg, completed: Math.floor(clamped) };
  }
  function distanceAtProgress(track, progress) {
    const last = track.at(-1);
    if (!last) return 0;
    if (progress >= track.length) return last.start + last.total;
    const leg = Math.max(0, Math.floor(progress));
    return track[leg].start + track[leg].total * Math.max(0, progress - leg);
  }
  function progressAtDistance(track, distance) {
    if (!track.length) return 0;
    const total = track.at(-1).start + track.at(-1).total;
    if (distance >= total) return track.length;
    if (distance <= 0) return 0;
    let low = 0, high = track.length - 1;
    while (low < high) { const middle = Math.floor((low + high) / 2); if (track[middle].start + track[middle].total <= distance) low = middle + 1; else high = middle; }
    return low + (track[low].total ? (distance - track[low].start) / track[low].total : 0);
  }
  function heading(track, progress) {
    const distance = distanceAtProgress(track, progress);
    const before = position(track, progressAtDistance(track, Math.max(0, distance - 5)));
    const after = position(track, progressAtDistance(track, distance + 5));
    return Math.hypot(after.x - before.x, after.y - before.y) < .001 ? position(track, progress).angle : Math.atan2(after.y - before.y, after.x - before.x) * 180 / Math.PI;
  }
  function turnAngle(current, target, elapsed) {
    const delta = ((target - current) % 360 + 540) % 360 - 180;
    return current + delta * (1 - Math.exp(-elapsed / 100));
  }
  function fitView(points, aspect, padding = 40) {
    if (!points.length || !(aspect > 0)) return [0, 0, 900, 550];
    const bounds = points.reduce((b, p) => [Math.min(b[0], p[0]), Math.max(b[1], p[0]), Math.min(b[2], p[1]), Math.max(b[3], p[1])], [Infinity, -Infinity, Infinity, -Infinity]);
    const [left, right, top, bottom] = bounds;
    const width = Math.max(80, right - left + padding * 2, (bottom - top + padding * 2) * aspect), height = width / aspect;
    return [(left + right - width) / 2, (top + bottom - height) / 2, width, height];
  }
  const api = { decodePolyline, buildTrack, position, fitView, distanceAtProgress, progressAtDistance, heading, turnAngle };
  if (typeof module !== "undefined") module.exports = api;
  else window.WaybillMotion = api;
}());
