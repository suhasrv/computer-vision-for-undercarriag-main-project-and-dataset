export function decodeMaskRLE(maskRleBase64) {
  // Placeholder: backend uses RLE (pycocotools) encoding. Implement client-side decode if needed.
  return null;
}

export function rgbaFromClass(className) {
  if (className === 'corrosion') return 'rgba(255,152,0,0.35)';
  if (className === 'dent' || className === 'dents') return 'rgba(255,60,60,0.35)';
  return 'rgba(0,200,255,0.35)';
}
