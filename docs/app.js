const progress = document.getElementById('progress');
window.addEventListener('scroll', () => {
  const max = document.documentElement.scrollHeight - innerHeight;
  progress.style.width = `${Math.max(0, Math.min(1, scrollY / max)) * 100}%`;
});
