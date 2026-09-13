// Original canvas scene: all world objects are game-native vector geometry.
export class FarmRenderer {
  constructor(canvas, onSelect) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.onSelect = onSelect;
    this.selected = null;
    this.state = null;
    this.drone = { x: 0, y: 0 };
    this.reduced = matchMedia('(prefers-reduced-motion: reduce)');
    this.last = 0;
    this.effect = null;
    new ResizeObserver(() => this.resize()).observe(canvas.parentElement);
    canvas.addEventListener('pointerdown', event => this.selectAt(event));
    requestAnimationFrame(time => this.animate(time));
  }
  resize() {
    const rect = this.canvas.getBoundingClientRect();
    this.width = rect.width;
    this.height = rect.height;
    const ratio = Math.min(devicePixelRatio || 1, 2);
    this.canvas.width = Math.round(rect.width * ratio);
    this.canvas.height = Math.round(rect.height * ratio);
    this.ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    this.layout();
    this.draw(performance.now());
  }
  layout() {
    if (!this.state) return;
    this.unit = this.width * (this.width < 500 ? .79 : .64) / (this.state.size * 2);
    this.half = this.unit * .51;
    this.originX = this.width * .51;
    this.originY = this.height * .465 - this.state.size * this.half;
  }
  update(state, action = null) {
    const first = !this.state;
    this.state = state;
    this.layout();
    if (first || this.reduced.matches || Math.abs(this.drone.x - state.drone.x) > 2 || Math.abs(this.drone.y - state.drone.y) > 2) this.drone = { ...state.drone };
    if (action === 'harvest' || action === 'water' || action === 'plant') this.effect = { action, x: state.drone.x, y: state.drone.y, start: performance.now() };
    this.canvas.setAttribute('aria-label', `${state.scenario === 'factory' ? 'Breadworks with chest, mill, oven, and delivery depot. ' : ''}${state.size} by ${state.size} farm. Drone at ${state.drone.x}, ${state.drone.y}. ${state.stats.harvested} crops harvested. Use Inspect plots for details.`);
    this.draw(performance.now());
  }
  point(x, y) { return { x: this.originX + (x - y) * this.unit, y: this.originY + (x + y) * this.half }; }
  polygon(points, fill, stroke = null, width = 1) {
    const c = this.ctx;
    c.beginPath(); points.forEach(([x, y], i) => i ? c.lineTo(x, y) : c.moveTo(x, y)); c.closePath();
    if (fill) { c.fillStyle = fill; c.fill(); }
    if (stroke) { c.strokeStyle = stroke; c.lineWidth = width; c.stroke(); }
  }
  ellipse(x, y, rx, ry, fill) {
    const c = this.ctx; c.beginPath(); c.ellipse(x, y, Math.max(rx, .1), Math.max(ry, .1), 0, 0, Math.PI * 2); c.fillStyle = fill; c.fill();
  }
  line(x, y, x2, y2, color, width = 1) {
    const c = this.ctx; c.beginPath(); c.moveTo(x, y); c.lineTo(x2, y2); c.strokeStyle = color; c.lineWidth = width; c.lineCap = 'round'; c.stroke();
  }
  diamond(x, y, u, v, color, stroke = null) { this.polygon([[x, y - v], [x + u, y], [x, y + v], [x - u, y]], color, stroke); }
  tree(x, y, scale, variant = 0) {
    this.ellipse(x + 10 * scale, y + 3 * scale, 24 * scale, 9 * scale, '#6f915529');
    this.ctx.fillStyle = '#84955d'; this.ctx.fillRect(x - 3 * scale, y - 19 * scale, 6 * scale, 20 * scale);
    const colors = variant ? ['#719457', '#86a667', '#9cb979'] : ['#6e8d56', '#7e9f60', '#92b36d'];
    this.polygon([[x - 23 * scale, y - 24 * scale], [x - 21 * scale, y - 49 * scale], [x - 7 * scale, y - 64 * scale], [x + 12 * scale, y - 62 * scale], [x + 24 * scale, y - 43 * scale], [x + 21 * scale, y - 20 * scale], [x, y - 13 * scale]], colors[0]);
    this.polygon([[x - 21 * scale, y - 49 * scale], [x - 7 * scale, y - 64 * scale], [x + 12 * scale, y - 62 * scale], [x + 13 * scale, y - 35 * scale], [x - 5 * scale, y - 25 * scale], [x - 23 * scale, y - 24 * scale]], colors[1]);
    this.polygon([[x - 19 * scale, y - 48 * scale], [x - 6 * scale, y - 61 * scale], [x + 9 * scale, y - 60 * scale], [x + 6 * scale, y - 45 * scale], [x - 7 * scale, y - 37 * scale]], colors[2]);
  }
  scene(time) {
    const c = this.ctx, w = this.width, h = this.height, s = Math.max(.45, Math.min(w / 750, 1.1));
    c.fillStyle = '#e4edcd'; c.fillRect(0, 0, w, h);
    this.polygon([[0, h * .28], [w * .28, 0], [w * .52, 0], [0, h * .58]], '#dce8c1');
    this.polygon([[w * .62, 0], [w, h * .23], [w, 0]], '#deE8c5');
    this.polygon([[0, h * .83], [w * .26, h], [0, h]], '#dce8c2');
    this.polygon([[w * .8, h * .41], [w, h * .25], [w, h * .63], [w * .93, h * .69]], '#dce6c2');
    // Stable, deterministic meadow texture.
    for (let i = 0; i < 135; i++) {
      const x = (i * 113.73 + 41) % w, y = (i * 79.31 + 23) % h;
      c.fillStyle = i % 5 === 0 ? '#c5d7a9' : '#d2e0b8';
      c.fillRect(x, y, 2 * s, 2 * s);
      if (i % 4 === 0) this.line(x, y, x - 2 * s, y - 3 * s, '#c2d3a4', 1);
    }
    // Farm lane and pond, outside the field.
    this.polygon([[w * .74, h * .17], [w * .82, h * .15], [w, h * .43], [w, h * .52]], '#d8dcb8');
    this.polygon([[w * .87, h * .29], [w * .92, h * .26], [w, h * .4], [w, h * .45]], '#e6e5c9');
    this.ellipse(w * .127, h * .725, 54 * s, 24 * s, '#cbdab1');
    this.ellipse(w * .127, h * .72, 46 * s, 18 * s, '#a2c7bd');
    this.ellipse(w * .127, h * .713, 39 * s, 14 * s, '#b1d3c5');
    this.line(w * .127 - 17 * s, h * .71, w * .127 + 3 * s, h * .71, '#d3e7d8', 2 * s);
    this.line(w * .127 + 8 * s, h * .735, w * .127 + 25 * s, h * .735, '#cce3d2', 1.5 * s);
    for (const [x, y] of [[.065,.32],[.15,.235],[.23,.14],[.83,.165],[.94,.27],[.9,.78],[.82,.83],[.04,.58]]) this.tree(w * x, h * y, s * (.62 + x % .3), Math.round(x * 10) % 2);
    // Small tool shed beside the farm lane.
    const bx = w * .85, by = h * .395, bw = 29 * s, bh = 22 * s;
    this.ellipse(bx + 8 * s, by + 5 * s, 40 * s, 11 * s, '#78935120');
    this.polygon([[bx - bw, by - bh], [bx, by - 9 * s], [bx, by + 15 * s], [bx - bw, by]], '#bbad7c');
    this.polygon([[bx, by - 9 * s], [bx + bw, by - bh], [bx + bw, by], [bx, by + 15 * s]], '#a99a6d');
    this.polygon([[bx - bw - 6 * s, by - bh], [bx - 3 * s, by - 44 * s], [bx + bw + 5 * s, by - 26 * s], [bx, by - 5 * s]], '#74876c');
    this.polygon([[bx - 3 * s, by - 44 * s], [bx + 13 * s, by - 42 * s], [bx + bw + 5 * s, by - 26 * s]], '#85947a');
    this.polygon([[bx + 7 * s, by - 5 * s], [bx + 18 * s, by - 10 * s], [bx + 18 * s, by + 5 * s], [bx + 7 * s, by + 11 * s]], '#6d7158');
    this.line(bx + 12 * s, by + 2 * s, bx + 12 * s, by + 6 * s, '#c9be8e', 1.5 * s);
    // A few daisies punctuate the meadow.
    for (const [x, y] of [[.27,.77],[.29,.79],[.73,.74],[.71,.77],[.19,.43],[.16,.42],[.67,.19]]) {
      this.line(w*x,h*y,w*x,h*y+4*s,'#97ad70',s);
      this.ellipse(w*x,h*y,2.5*s,2*s,'#fbf9db'); this.ellipse(w*x,h*y,1*s,1*s,'#d6c66a');
    }
  }
  crop(x, y, tile, variation = 0) {
    const c = this.ctx, scale = this.unit / 32;
    const max = { wheat: 6, carrot: 9, sunflower: 12 }[tile.crop];
    const grown = tile.growth / max;
    const height = (6 + 15 * grown) * scale;
    if (grown < .35) {
      this.line(x, y, x, y - height, '#6b9248', 2 * scale);
      this.ellipse(x - 3 * scale, y - height * .65, 4 * scale, 2 * scale, '#92b36b');
      this.ellipse(x + 3 * scale, y - height, 4 * scale, 2 * scale, '#7aa653');
      return;
    }
    if (tile.crop === 'wheat') {
      const color = grown >= 1 ? '#d9bf64' : '#94aa56';
      for (const offset of [-5, 0, 5]) {
        const px = x + offset * scale, py = y - height + Math.abs(offset) * .5 * scale;
        this.line(px, y + 1 * scale, px, py - 3 * scale, '#a5a052', 1.5 * scale);
        for (let j = 0; j < 3; j++) {
          this.line(px, py + j * 3.8 * scale, px - 3 * scale, py + (j * 3.8 - 3) * scale, color, 2.5 * scale);
          this.line(px, py + j * 3.8 * scale, px + 3 * scale, py + (j * 3.8 - 3) * scale, color, 2.5 * scale);
        }
      }
    } else if (tile.crop === 'carrot') {
      this.ellipse(x, y, 5 * scale, 3 * scale, grown >= 1 ? '#d39247' : '#b6a364');
      for (const offset of [-6, 0, 6]) this.line(x, y, x + offset * scale, y - height + Math.abs(offset) * scale, '#7a9950', 2.4 * scale);
      this.line(x,y-5*scale,x-8*scale,y-10*scale,'#95ae68',2*scale);
      this.line(x,y-4*scale,x+8*scale,y-8*scale,'#78974e',2*scale);
    } else {
      this.line(x, y, x, y - height, '#829449', 2 * scale);
      this.ellipse(x - 4 * scale,y-height*.4,5*scale,2*scale,'#819b4e');
      this.ellipse(x + 4 * scale,y-height*.65,5*scale,2*scale,'#95aa58');
      this.ellipse(x, y - height, 6.5 * scale, 6.5 * scale, grown >= 1 ? '#e3bc54' : '#b4b76a');
      this.ellipse(x, y - height, 3 * scale, 3 * scale, '#8c7950');
    }
  }
  building(name, p, time) {
    const c = this.ctx, u = this.unit, z = u * .55;
    const colors = {chest: ['#b39463','#8c734d','#d3b67e'], mill: ['#dbd9bc','#aaa98c','#7f987f'], oven: ['#c99173','#996e57','#d3ad87'], depot: ['#99b3a0','#6a8975','#cbd7ba']}[name];
    this.diamond(p.x,p.y,u*.9,this.half*.85,'#ecebd9','#b8baa0');
    this.polygon([[p.x-z,p.y-z*.4],[p.x,p.y],[p.x,p.y-z],[p.x-z,p.y-z*1.4]], colors[0]);
    this.polygon([[p.x,p.y],[p.x+z,p.y-z*.4],[p.x+z,p.y-z*1.4],[p.x,p.y-z]],colors[1]);
    this.diamond(p.x,p.y-z*1.4,z,z*.4,colors[2],'#7f866b');
    if(name==='mill') {
      const angle = this.state.machines.mill.remaining && !this.reduced.matches ? time/550 : .6;
      const cx=p.x, cy=p.y-z*1.9;
      for(let i=0;i<4;i++) { const a=angle+i*Math.PI/2; this.line(cx,cy,cx+Math.cos(a)*z*.9,cy+Math.sin(a)*z*.9,'#f9f5da',3); }
      this.ellipse(cx,cy,2,2,'#667760');
    } else if(name==='oven') {
      this.polygon([[p.x+z*.15,p.y-z*.5],[p.x+z*.7,p.y-z*.72],[p.x+z*.7,p.y-z*.24],[p.x+z*.15,p.y-z*.02]],'#655346');
      this.ellipse(p.x+z*.43,p.y-z*.4,z*.17,z*.14,this.state.machines.oven.remaining?'#f1c273':'#b49b74');
      c.fillStyle='#9e8065';c.fillRect(p.x+z*.35,p.y-z*2,z*.3,z*.7);
    } else if(name==='chest') {
      this.line(p.x-z*.55,p.y-z*1.5,p.x-z*.55,p.y-z*.6,'#eee2af',2);
      this.line(p.x+z*.55,p.y-z*1.5,p.x+z*.55,p.y-z*.6,'#eee2af',2);
    } else {
      this.line(p.x-z*.65,p.y-z*.3,p.x-z*.65,p.y-z*2.5,'#6b8068',2);
      this.polygon([[p.x-z*.65,p.y-z*2.5],[p.x+z*.05,p.y-z*2.3],[p.x-z*.65,p.y-z*1.9]],'#d9be79');
    }
  }
  draw(time) {
    if (!this.width || !this.state) return;
    this.scene(time);
    const c = this.ctx, s = this.state, u = this.unit, v = this.half, n = s.size;
    const top = this.point(0, 0), right = this.point(n, 0), bottom = this.point(n, n), left = this.point(0, n);
    this.polygon([[left.x-9,left.y+7],[bottom.x,bottom.y+14],[right.x+12,right.y+9],[bottom.x+3,bottom.y+23]], '#76905524');
    this.polygon([[left.x-5,left.y],[bottom.x,bottom.y+5],[bottom.x,bottom.y+14],[left.x-5,left.y+9]], '#a3b57e');
    this.polygon([[bottom.x,bottom.y+5],[right.x+5,right.y],[right.x+5,right.y+9],[bottom.x,bottom.y+14]], '#91a66f');
    this.polygon([[top.x,top.y-5],[right.x+5,right.y],[bottom.x,bottom.y+5],[left.x-5,left.y]], '#b9c899');
    for (let sum = 0; sum < n * 2 - 1; sum++) for (let y = 0; y < n; y++) {
      const x = sum - y;
      if (x < 0 || x >= n) continue;
      const tile = s.tiles[y*n+x], p = this.point(x+.5,y+.5);
      const factory = s.scenario === 'factory';
      const paved = factory && (x >= this.catalog.field.width || y >= this.catalog.field.height);
      const base = paved ? ((x+y)%2 ? '#d3d5bb' : '#dcdec7') : tile.tilled ? (tile.water ? '#99896b' : '#b39c77') : ((x+y)%2 ? '#c2ce9a' : '#cbd5a4');
      this.diamond(p.x,p.y,u-1,v-1,base,tile.tilled ? '#a8906d' : '#b8c58f');
      if (tile.tilled) {
        for (let j = -.5; j <= .5; j += .5) {
          const start = this.point(x+.13,y+.5+j*.62), end = this.point(x+.83,y+.5+j*.62);
          this.line(start.x,start.y,end.x,end.y,tile.water ? '#877c61' : '#a38e6a',1.3);
        }
      } else if (!paved) {
        const offset = (x * 7 + y * 11) % 3;
        this.line(p.x-5,p.y-2,p.x-7,p.y-5,'#a8bc80',1);
        this.line(p.x-4,p.y-2,p.x-3,p.y-5,'#b0c489',1);
        if (offset === 0) this.ellipse(p.x+9,p.y+2,1.5,1,'#e3e7bb');
      }
      if (this.selected?.x === x && this.selected?.y === y) this.diamond(p.x,p.y,u-2,v-2,'#ffffff10','#f3f4cd');
      if (s.drone.x === x && s.drone.y === y) this.diamond(p.x,p.y,u-2,v-2,'#edf5bf25','#ecf2b5');
      if (factory && this.catalog.obstacles.some(([ox,oy]) => ox === x && oy === y)) {
        this.polygon([[p.x-u*.5,p.y],[p.x-u*.35,p.y-u*.6],[p.x+u*.2,p.y-u*.7],[p.x+u*.5,p.y-u*.1],[p.x+u*.1,p.y+u*.2]], '#969e88', '#828c77');
        this.line(p.x-u*.35,p.y-u*.6,p.x+u*.05,p.y-u*.3,'#b6bca4',2);
      }
      if (factory) for (const [name,entity] of Object.entries(this.catalog.entities)) {
        if(entity.x===x && entity.y===y) this.building(name,p,time);
      }
      if (tile.crop) {
        for (const [dx,dy] of [[-.3,-.02],[.26,-.03],[0,.29]]) this.crop(p.x+dx*u,p.y+dy*v,tile);
      }
    }
    // Labels sit above the finished ground layer so foreground tiles cannot erase them.
    if(s.scenario==='factory') for(const [name,entity] of Object.entries(this.catalog.entities)) {
      const p=this.point(entity.x+.5,entity.y+.5);
      c.font='600 '+Math.max(9,Math.min(11,u*.48))+'px ui-monospace, monospace';c.textAlign='center';
      const width=c.measureText(name).width+12;
      c.fillStyle='#f9f9ecee';c.fillRect(p.x-width/2,p.y+v*.7,width,16);
      c.fillStyle='#4d6249';c.fillText(name,p.x,p.y+v*.7+11);
    }
    // Coordinate markers along the two near field edges.
    c.font = `${Math.max(9, Math.min(11, u*.35))}px ui-monospace, monospace`; c.fillStyle = '#92a177'; c.textAlign = 'center';
    for(let i=0;i<n;i++) { const a=this.point(n+.36,i+.5), b=this.point(i+.5,n+.4); c.fillText(String(i),a.x,a.y+4); c.fillText(String(i),b.x,b.y+4); }
    const p = this.point(this.drone.x + .5, this.drone.y + .5);
    const ds = Math.max(.66, Math.min(u/28,1.25));
    const bob = this.reduced.matches ? 0 : Math.sin(time/450)*1.5;
    this.ellipse(p.x+2,p.y+4,15*ds,6*ds,'#3e54252b');
    const dy = p.y-31*ds+bob;
    if (this.effect && time-this.effect.start < 600 && !this.reduced.matches) {
      const t=(time-this.effect.start)/600, e=this.point(this.effect.x+.5,this.effect.y+.5);
      for(let i=0;i<7;i++) {const angle=i/7*Math.PI*2;this.ellipse(e.x+Math.cos(angle)*t*28*ds,e.y-10+Math.sin(angle)*t*12*ds-t*15,2*(1-t)*ds,2*(1-t)*ds,this.effect.action==='water'?'#7faebe':'#e9d27a');}
    }
    for(const [dx,oy] of [[-16,-5],[16,-5],[-16,8],[16,8]]) {
      this.line(p.x,dy+2,p.x+dx*ds,dy+oy*ds,'#738578',4*ds);
      this.ellipse(p.x+dx*ds,dy+oy*ds,9*ds,4.5*ds,'#526a5f');
      this.ellipse(p.x+dx*ds,dy+oy*ds-.6,7.5*ds,3.5*ds,'#dae4cb');
      const angle=this.reduced.matches?.3:time/35+dx;
      this.line(p.x+dx*ds-Math.cos(angle)*8*ds,dy+oy*ds-Math.sin(angle)*3*ds,p.x+dx*ds+Math.cos(angle)*8*ds,dy+oy*ds+Math.sin(angle)*3*ds,'#9cafa0',1.7*ds);
    }
    this.polygon([[p.x-9*ds,dy-9*ds],[p.x+8*ds,dy-9*ds],[p.x+11*ds,dy+3*ds],[p.x+5*ds,dy+9*ds],[p.x-9*ds,dy+6*ds]],'#e9eee0','#6d8272');
    this.polygon([[p.x-5*ds,dy-5*ds],[p.x+5*ds,dy-5*ds],[p.x+6*ds,dy+1*ds],[p.x-5*ds,dy+1*ds]],'#91a893');
    this.ellipse(p.x,dy+5*ds,2*ds,1.6*ds,'#e5c660');
  }
  animate(time) {
    if (this.state && time - this.last > 32 && !document.hidden) {
      const factor = this.reduced.matches ? 1 : .22;
      this.drone.x += (this.state.drone.x - this.drone.x) * factor;
      this.drone.y += (this.state.drone.y - this.drone.y) * factor;
      this.draw(time); this.last = time;
    }
    requestAnimationFrame(next => this.animate(next));
  }
  selectAt(event) {
    if (!this.state) return;
    const rect=this.canvas.getBoundingClientRect(), dx=(event.clientX-rect.left-this.originX)/this.unit, dy=(event.clientY-rect.top-this.originY)/this.half;
    const x=Math.floor((dx+dy)/2), y=Math.floor((dy-dx)/2);
    if(x>=0&&y>=0&&x<this.state.size&&y<this.state.size) {this.selected={x,y};this.onSelect(x,y);this.draw(performance.now());}
  }
}
