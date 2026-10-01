document.addEventListener('DOMContentLoaded', function () {
  var $ = function (s) { return document.querySelector(s); };
  var b = $('#burger'), m = $('#menu');
  if (b) b.onclick = function () { m.classList.toggle('open'); };
  var f = $('#forgot');
  if (f) f.onclick = function (e) { e.preventDefault(); alert('Demo project: use username "demo" and password "demo123".'); };
  var sf = $('#searchform');
  if (sf) sf.addEventListener('submit', function (e) {
    if (sf.from.value && sf.from.value === sf.to.value) {
      e.preventDefault(); alert('Source and destination cannot be the same.');
    }
  });
  var eb = $('#editbtn');
  if (eb) eb.onclick = function () { $('#editform').hidden = false; $('#view').hidden = true; eb.hidden = true; };
  document.querySelectorAll('.flash.success').forEach(function (el) {
    setTimeout(function () { el.style.opacity = 0; }, 6000);
  });
});
