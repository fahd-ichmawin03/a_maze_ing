"""
maze_renderer.py — Browser-based HTML/Canvas renderer for A-Maze-ing.

Generates a self-contained HTML file and opens it in the default browser.
All interactions happen client-side (no server needed).

Subject requirements covered:
    1. Re-generate a new maze and display it.
    2. Show / Hide shortest path from entry to exit.
    3. Change maze wall colours (5 palettes).
    4. (Optional) Set specific colour for the "42" pattern.

Usage:
    from maze_renderer import TerminalRenderer
    renderer = TerminalRenderer(gen, cfg)
    renderer.run()
"""

import json
import os
import sys
import tempfile
import webbrowser

from mazegen.maze_generator import (
    MazeGenerator,
    NORTH, EAST, SOUTH, WEST,
)
from config_parser import MazeConfig


# ---------------------------------------------------------------------------
# HTML template — self-contained single file, no external deps
# ---------------------------------------------------------------------------

_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>A-Maze-ing</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: ui-monospace, 'Cascadia Code', 'Fira Mono', monospace;
    background: #111;
    color: #eee;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 24px 16px 32px;
    min-height: 100vh;
    gap: 18px;
  }
  h1 { font-size: 18px; font-weight: 500; letter-spacing: .08em; color: #ccc; }
  #canvas-wrap {
    position: relative;
    line-height: 0;
  }
  canvas {
    display: block;
    border: 1.5px solid #333;
    border-radius: 6px;
    cursor: default;
  }
  .controls {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    justify-content: center;
    max-width: 700px;
  }
  button {
    font-family: inherit;
    font-size: 13px;
    padding: 7px 16px;
    border: 1px solid #444;
    border-radius: 6px;
    background: #1e1e1e;
    color: #ddd;
    cursor: pointer;
    transition: background .15s, border-color .15s;
  }
  button:hover  { background: #2a2a2a; border-color: #666; }
  button.active { background: #1d4a38; border-color: #1d9e75; color: #5dca99; }
  button#btnRegen { border-color: #4a3d1d; color: #c8a43a; }
  button#btnRegen:hover { background: #2a2010; border-color: #c8a43a; }
  .palette-dot {
    display: inline-block;
    width: 10px; height: 10px;
    border-radius: 50%;
    margin-right: 6px;
    vertical-align: middle;
  }
  .info {
    font-size: 12px;
    color: #666;
    letter-spacing: .04em;
  }
  .legend {
    display: flex;
    gap: 16px;
    font-size: 12px;
    color: #888;
    flex-wrap: wrap;
    justify-content: center;
  }
  .legend span { display: flex; align-items: center; gap: 6px; }
  .swatch {
    width: 14px; height: 14px;
    border-radius: 3px;
    display: inline-block;
    flex-shrink: 0;
  }
</style>
</head>
<body>

<h1>A-Maze-ing</h1>

<div id="canvas-wrap"><canvas id="c"></canvas></div>

<div class="controls">
  <button id="btnRegen">↺  New maze</button>
  <button id="btnPath">Show solution</button>
  <button id="btnWall">Wall colour</button>
  <button id="btn42">Highlight 42</button>
</div>

<div class="legend">
  <span><span class="swatch" id="sw-entry"></span>Entry</span>
  <span><span class="swatch" id="sw-exit"></span>Exit</span>
  <span><span class="swatch" id="sw-path"></span>Solution</span>
  <span><span class="swatch" id="sw-42"></span>"42" pattern</span>
</div>

<div class="info" id="info"></div>

<script>
const MAZE_DATA = __MAZE_DATA__;

const NORTH=1,EAST=2,SOUTH=4,WEST=8;
const OPP={[NORTH]:SOUTH,[SOUTH]:NORTH,[EAST]:WEST,[WEST]:EAST};
const DX={[NORTH]:0,[EAST]:1,[SOUTH]:0,[WEST]:-1};
const DY={[NORTH]:-1,[EAST]:0,[SOUTH]:1,[WEST]:0};

/* ---- Palettes: [wallColour, bgColour] ---- */
const PALETTES = [
  ['#e8e8e8', '#111'],
  ['#f5c842', '#1a1400'],
  ['#5dca99', '#041a10'],
  ['#85b7eb', '#04111f'],
  ['#f0997b', '#1f0804'],
];
let palIdx = 0;

/* ---- Special colours ---- */
const C_ENTRY  = '#7f77dd';
const C_EXIT   = '#d85a30';
const C_PATH   = '#1d9e75';
const C_42_ON  = '#c8a43a';
const C_42_OFF = '#333';

let showPath   = false;
let show42     = true;    /* highlight 42 by default */
let grid       = null;    /* current grid [row][col] bitmask */
let path       = [];      /* solution cell list */
let cells42    = new Set();
let W, H, entryX, entryY, exitX, exitY;

/* ---- rng (xorshift, reproducible) ---- */
function makeRng(seed){
  let x = seed >>> 0 || 1;
  return () => {
    x ^= x << 13; x ^= x >>> 17; x ^= x << 5;
    return (x >>> 0) / 4294967296;
  };
}

/* ---- Load initial maze from Python-injected data ---- */
function loadInitial(){
  W        = MAZE_DATA.width;
  H        = MAZE_DATA.height;
  entryX   = MAZE_DATA.entry[0];
  entryY   = MAZE_DATA.entry[1];
  exitX    = MAZE_DATA.exit[0];
  exitY    = MAZE_DATA.exit[1];
  grid     = MAZE_DATA.grid;          /* array of rows, each row = array of ints */
  cells42  = new Set(MAZE_DATA.cells42.map(([x,y]) => y*W+x));
  path     = MAZE_DATA.path;
}

/* ---- Generate a new maze client-side (recursive backtracker) ---- */
function generate(seed){
  const r   = makeRng(seed);
  const g   = Array.from({length:H}, () => new Uint8Array(W));
  const vis = new Uint8Array(W*H);
  const stk = [[entryX, entryY]];
  vis[entryY*W+entryX] = 1;

  /* pre-close "42" cells */
  const c42 = compute42cells(W, H);
  cells42   = new Set(c42.map(([x,y]) => y*W+x));

  while(stk.length){
    const [x,y] = stk[stk.length-1];
    const dirs = [NORTH,EAST,SOUTH,WEST].sort(()=>r()-0.5);
    let moved = false;
    for(const d of dirs){
      const nx=x+DX[d], ny=y+DY[d];
      if(nx<0||nx>=W||ny<0||ny>=H) continue;
      if(vis[ny*W+nx]) continue;
      if(cells42.has(ny*W+nx)) continue;  /* skip 42 cells */
      g[y][x]|=d; g[ny][nx]|=OPP[d];
      vis[ny*W+nx]=1; stk.push([nx,ny]); moved=true; break;
    }
    if(!moved) stk.pop();
  }

  /* stamp 42 cells (all walls closed) */
  for(const k of cells42){
    const cy=Math.floor(k/W), cx=k%W;
    g[cy][cx] = NORTH|EAST|SOUTH|WEST;
  }

  /* border walls */
  for(let x=0;x<W;x++){ g[0][x]|=NORTH; g[H-1][x]|=SOUTH; }
  for(let y=0;y<H;y++){ g[y][0]|=WEST;  g[y][W-1]|=EAST;  }

  /* open entry/exit outer wall */
  if(entryY===0)         g[entryY][entryX]&=~NORTH;
  else if(entryY===H-1)  g[entryY][entryX]&=~SOUTH;
  else if(entryX===0)    g[entryY][entryX]&=~WEST;
  else                   g[entryY][entryX]&=~EAST;
  if(exitY===0)          g[exitY][exitX]&=~NORTH;
  else if(exitY===H-1)   g[exitY][exitX]&=~SOUTH;
  else if(exitX===0)     g[exitY][exitX]&=~WEST;
  else                   g[exitY][exitX]&=~EAST;

  grid = g;
  path = bfs(entryX, entryY, exitX, exitY);
}

/* ---- Compute "42" cell positions (same logic as Python) ---- */
function compute42cells(w, h){
  const FOUR = ['101','101','111','001','001'];
  const TWO  = ['111','001','111','100','111'];
  const dw=3, dh=5, gap=1, pw=dw*2+gap;
  if(w < pw+4 || h < dh+4) return [];
  const ox=Math.floor((w-pw)/2), oy=Math.floor((h-dh)/2);
  const cells=[];
  [[FOUR,0],[TWO,dw+gap]].forEach(([digit,dxOff])=>{
    digit.forEach((row,ri)=>{
      [...row].forEach((px,ci)=>{
        if(px==='1'){
          const cx=ox+dxOff+ci, cy=oy+ri;
          if(cx>=0&&cx<w&&cy>=0&&cy<h) cells.push([cx,cy]);
        }
      });
    });
  });
  /* don't block entry/exit */
  return cells.filter(([x,y])=>!(x===entryX&&y===entryY)&&!(x===exitX&&y===exitY));
}

/* ---- BFS shortest path ---- */
function bfs(sx,sy,ex,ey){
  const prev={};
  const vis=new Uint8Array(W*H); vis[sy*W+sx]=1;
  const q=[[sx,sy]];
  while(q.length){
    const [x,y]=q.shift();
    if(x===ex&&y===ey) break;
    for(const d of [NORTH,EAST,SOUTH,WEST]){
      if(!(grid[y][x]&d)) continue;
      const nx=x+DX[d], ny=y+DY[d];
      if(nx<0||nx>=W||ny<0||ny>=H||vis[ny*W+nx]) continue;
      if(cells42.has(ny*W+nx)) continue;
      vis[ny*W+nx]=1; prev[ny*W+nx]={x,y}; q.push([nx,ny]);
    }
  }
  const p=[]; let cx=ex, cy=ey;
  while(prev[cy*W+cx]){const {x,y}=prev[cy*W+cx]; p.unshift([cx,cy]); cx=x; cy=y;}
  p.unshift([sx,sy]); return p;
}

/* ---- Draw ---- */
function draw(){
  const canvas = document.getElementById('c');
  /* dynamic cell size: fit into ~min(window.innerWidth-64, 700) */
  const maxPx  = Math.min(window.innerWidth - 64, 720);
  const CELL   = Math.max(14, Math.floor(maxPx / Math.max(W, H)));
  const CW     = W*CELL+1, CH = H*CELL+1;
  canvas.width=CW; canvas.height=CH;
  const ctx=canvas.getContext('2d');

  const [wallC, bgC] = PALETTES[palIdx];

  /* background */
  ctx.fillStyle=bgC; ctx.fillRect(0,0,CW,CH);

  /* "42" cells fill */
  const c42color = show42 ? C_42_ON : '#2a2a2a';
  for(const k of cells42){
    const cy=Math.floor(k/W), cx=k%W;
    ctx.fillStyle=c42color;
    ctx.fillRect(cx*CELL+1, cy*CELL+1, CELL-1, CELL-1);
  }

  /* solution path */
  if(showPath && path.length>1){
    ctx.save();
    ctx.strokeStyle=C_PATH;
    ctx.lineWidth=Math.max(2, CELL*0.28);
    ctx.lineCap='round'; ctx.lineJoin='round';
    ctx.beginPath();
    path.forEach(([x,y],i)=>{
      const px=x*CELL+CELL/2, py=y*CELL+CELL/2;
      i===0 ? ctx.moveTo(px,py) : ctx.lineTo(px,py);
    });
    ctx.stroke();
    ctx.restore();
  }

  /* entry / exit highlight */
  const alpha=(c,a)=>c+Math.round(a*255).toString(16).padStart(2,'0');
  ctx.fillStyle=alpha(C_ENTRY,'50'); 
  ctx.fillRect(entryX*CELL+1, entryY*CELL+1, CELL-1, CELL-1);
  ctx.fillStyle=alpha(C_EXIT,'50');
  ctx.fillRect(exitX*CELL+1, exitY*CELL+1, CELL-1, CELL-1);

  /* walls */
  ctx.strokeStyle=wallC;
  ctx.lineWidth=1.6;
  ctx.lineCap='square';

  for(let y=0;y<H;y++){
    for(let x=0;x<W;x++){
      const px=x*CELL, py=y*CELL;
      const v=grid[y][x];
      ctx.beginPath();
      if(!(v&NORTH)){ctx.moveTo(px,py);      ctx.lineTo(px+CELL,py);}
      if(!(v&EAST)) {ctx.moveTo(px+CELL,py); ctx.lineTo(px+CELL,py+CELL);}
      if(!(v&SOUTH)){ctx.moveTo(px,py+CELL); ctx.lineTo(px+CELL,py+CELL);}
      if(!(v&WEST)) {ctx.moveTo(px,py);      ctx.lineTo(px,py+CELL);}
      ctx.stroke();
    }
  }

  /* outer border (always full) */
  ctx.lineWidth=2; ctx.strokeStyle=wallC;
  ctx.strokeRect(0,0,CW,CH);

  /* entry / exit dots */
  const dot=(x,y,c)=>{
    ctx.beginPath();
    ctx.arc(x*CELL+CELL/2, y*CELL+CELL/2, Math.max(3,CELL*0.2), 0, Math.PI*2);
    ctx.fillStyle=c; ctx.fill();
  };
  dot(entryX,entryY,C_ENTRY);
  dot(exitX,  exitY, C_EXIT);

  /* info */
  document.getElementById('info').textContent =
    `${W}\u00d7${H} \u00b7 algorithm: __ALGO__ \u00b7 perfect: __PERFECT__ \u00b7 solution: ${path.length-1} steps`;

  /* swatches */
  document.getElementById('sw-entry').style.background=C_ENTRY;
  document.getElementById('sw-exit').style.background=C_EXIT;
  document.getElementById('sw-path').style.background=C_PATH;
  document.getElementById('sw-42').style.background=show42?C_42_ON:'#555';
}

/* ---- Button handlers ---- */
document.getElementById('btnRegen').onclick = () => {
  generate(Math.random()*2**32|0);
  showPath=false;
  document.getElementById('btnPath').classList.remove('active');
  document.getElementById('btnPath').textContent='Show solution';
  draw();
};

document.getElementById('btnPath').onclick = () => {
  showPath=!showPath;
  const btn=document.getElementById('btnPath');
  btn.classList.toggle('active', showPath);
  btn.textContent=showPath?'Hide solution':'Show solution';
  draw();
};

document.getElementById('btnWall').onclick = () => {
  palIdx=(palIdx+1)%PALETTES.length;
  draw();
};

document.getElementById('btn42').onclick = () => {
  show42=!show42;
  const btn=document.getElementById('btn42');
  btn.classList.toggle('active', show42);
  btn.textContent=show42?'42: coloured':'42: hidden';
  draw();
};

window.addEventListener('resize', draw);

/* ---- Boot ---- */
loadInitial();
draw();
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Python helper — build the JSON payload injected into the HTML
# ---------------------------------------------------------------------------

def _maze_to_json(gen: MazeGenerator) -> str:
    """Serialise the maze into a JSON object for the HTML template.

    Args:
        gen: A generated MazeGenerator instance.

    Returns:
        JSON string.
    """
    return json.dumps({
        "width":   gen.width,
        "height":  gen.height,
        "entry":   list(gen.entry),
        "exit":    list(gen.exit_),
        "grid":    [list(row) for row in gen.grid],
        "cells42": [list(c) for c in sorted(gen._42_cells)],
        "path":    [list(p) for p in gen.solution],
    })


# ---------------------------------------------------------------------------
# Renderer class
# ---------------------------------------------------------------------------

class TerminalRenderer:
    """Opens the maze in the default web browser as a self-contained HTML file.

    Despite the class name (kept for compatibility with a_maze_ing.py) this
    renderer uses an HTML canvas — not a terminal — for a clean visual output.

    Args:
        gen: A generated MazeGenerator instance.
        cfg: The validated MazeConfig.
    """

    def __init__(self, gen: MazeGenerator, cfg: MazeConfig) -> None:
        """Initialise the renderer."""
        self._gen: MazeGenerator = gen
        self._cfg: MazeConfig = cfg

    def run(self) -> None:
        """Build the HTML file, open it in the browser, then wait for input.

        The HTML file is written to a temporary file that persists until the
        user presses Enter (so the browser can load it).
        """
        html = self._build_html()

        try:
            tmp = tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".html",
                prefix="a_maze_ing_",
                delete=False,
                encoding="utf-8",
            )
            tmp.write(html)
            tmp.flush()
            tmp_path = tmp.name
            tmp.close()
        except OSError as e:
            print(f"[ERROR] Cannot write HTML file: {e}", file=sys.stderr)
            sys.exit(1)

        url = f"file://{os.path.abspath(tmp_path)}"
        print(f"[OK] Opening maze in browser: {url}")
        webbrowser.open(url)
        print("Press Enter to quit (the browser tab will stay open)…")
        try:
            input()
        except (KeyboardInterrupt, EOFError):
            pass
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    def _build_html(self) -> str:
        """Render the full HTML string.

        Returns:
            Self-contained HTML page as a string.
        """
        maze_json = _maze_to_json(self._gen)
        algo      = self._cfg.algorithm.replace("_", " ")
        perfect   = str(self._cfg.perfect).lower()

        return (
            _HTML_TEMPLATE
            .replace("__MAZE_DATA__", maze_json)
            .replace("__ALGO__",     algo)
            .replace("__PERFECT__",  perfect)
        )


# ---------------------------------------------------------------------------
# Standalone usage
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from config_parser import parse_config

    cfg_path = sys.argv[1] if len(sys.argv) > 1 else "config.txt"
    try:
        cfg = parse_config(cfg_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)

    gen = MazeGenerator(
        width=cfg.width,
        height=cfg.height,
        entry=cfg.entry,
        exit_=cfg.exit_,
        perfect=cfg.perfect,
        seed=cfg.seed,
        algorithm=cfg.algorithm,
    )
    gen.generate()
    TerminalRenderer(gen, cfg).run()