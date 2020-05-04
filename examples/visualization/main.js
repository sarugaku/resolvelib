var dotSourceList = {{ dot_source_list|tojson }};

var state = {
  transitionDelay: 0,
  index: 0,
  playing: false,
}
var controls = {
  index: null,
  buttons: {
    next: null,
    prev: null,
    toggle: null,
  },
  slider: null,
}
var graph = null;

/////////////
// Helpers //
/////////////
// From https://stackoverflow.com/a/37623959/1931274
function onRangeChange(r, f) {
  var n, c, m;
  r.addEventListener("input", function (e) {
    n = 1; c = e.target.value; if (c != m) { f(e); }; m = c;
  });
  r.addEventListener("change", function (e) { if (!n) { f(e); }});
}

//////////////
// UI Logic //
//////////////
function setupControls() {
  controls.index = document.getElementById("index");

  controls.buttons.next = document.getElementById("next");
  controls.buttons.next.onclick = showNext;

  controls.buttons.prev = document.getElementById("prev");
  controls.buttons.prev.onclick = showPrevious;

  controls.buttons.toggle = document.getElementById("toggle");
  controls.buttons.toggle.onclick = toggle;

  controls.slider = document.getElementById("slider");
  controls.slider.setAttribute("max", dotSourceList.length - 1);
  onRangeChange(controls.slider, showSliderState);

}

function updateControls() {
  controls.slider.value = state.index;
  controls.index.innerHTML = state.index;

  if (state.playing) {
    controls.buttons.toggle.innerHTML = "Pause";
  } else {
    controls.buttons.toggle.innerHTML = "Play";
  }
}

//////////////////
// UI callbacks //
//////////////////
function toggle() {
  console.log("toggle");
  state.playing = !state.playing;
  showThisGraph();
}

function showNext() {
  console.log("next");
  state.playing = false;
  if (state.index < dotSourceList.length - 1) {
    state.index = state.index + 1;
  }
  showThisGraph();
}

function showPrevious() {
  console.log("previous");
  state.playing = false;
  if (state.index != 0) {
    state.index = state.index - 1;
  }
  showThisGraph();
}

function showSliderState() {
  console.log("slider");
  var value = Number(controls.slider.value);
  state.index = value;
  state.playing = false;

  showThisGraph();
}

///////////////
// Rendering //
///////////////
function prepareGraph() {
  graph = d3.select("#graph").graphviz();
  graph
    .zoom(false)
    .transition(function () {
      return d3.transition("main")
        .ease(d3.easeExpOut)
        .duration(750)
        .delay(state.transitionDelay);
    })
    .on("initEnd", showThisGraph);

}

function showThisGraph() {
  updateControls();

  var dotSource = dotSourceList[state.index];
  return graph
    .renderDot(dotSource)
    // The following sets up the "play" mode.
    .on("end", continueIfPlaying);
}


function continueIfPlaying() {
  if (!state.playing) {
    return
  }
  state.index = (state.index + 1) % dotSourceList.length;
  showThisGraph();
}

/////////////////
// Entry Point //
/////////////////
function main() {
  setupControls();
  prepareGraph();
}

document.addEventListener("DOMContentLoaded", main);
