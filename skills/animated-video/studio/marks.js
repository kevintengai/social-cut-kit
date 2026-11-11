(function (root) {
  "use strict";
  const paths = {
    Aperture: ["M12 5L25 4 36 12 37 25 29 36 16 37 5 29 4 16Z", "M12 5L21 18 36 12M37 25L22 26 16 37M5 29L14 18 4 16", "M21 18L25 24 19 29 14 23 15 18Z"],
    Signal: ["M4 26L10 26 15 12 22 34 28 7 33 20 39 20", "M5 36L10 36M33 30L38 30"],
    Focus: ["M4 15L4 5 14 5M28 5L38 5 38 15M38 27L38 37 28 37M14 37L4 37 4 27", "M14 21L28 21M21 14L21 28"],
    Route: ["M7 32L15 32Q20 32 20 27L20 15Q20 10 25 10L35 10M29 4L36 10 29 16", "M6 28A4 4 0 1 1 5.99 28"],
    Spark: ["M22 3L24 15 37 18 25 22 22 37 18 24 5 21 17 16Z", "M6 5L10 9M34 29L38 34"],
    Orbit: ["M5 29C-1 21 29 5 36 11 43 18 12 35 5 29Z", "M29 25A12 12 0 1 1 25 9", "M31 8L36 6"]
  };
  const api = { paths };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.MotionMarks = api;
})(globalThis);
