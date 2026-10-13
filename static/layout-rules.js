// Presentation mirrors the catalog's fixed terrain; Python validates every apply.
export function withPositions(definitions, positions = {}) {
  return Object.fromEntries(Object.entries(definitions).map(([name, rule]) => [name, {...rule, ...positions[name]}]));
}

export function layoutEntities(state, catalog, positions = state.layout?.positions || {}) {
  const definitions = state.recycling ? {...catalog.entities, ...catalog.recycling.entities} : catalog.entities;
  return withPositions(definitions, positions);
}

export function validatePositions(state, catalog, positions) {
  const definitions = {...catalog.entities, ...catalog.recycling.entities};
  for (const [name, point] of Object.entries(positions)) {
    if (!catalog.layout.movable.includes(name) || ['composter','mixer'].includes(name) && !state.recycling) return 'Choose an installed machine.';
    if (!point || !Number.isInteger(point.x) || !Number.isInteger(point.y) || point.x < 0 || point.x > 7 || point.y < 0 || point.y > 7) return 'Coordinates must be whole numbers from 0 to 7.';
    if (point.x < catalog.field.width && point.y < catalog.field.height) return 'Growing plots are reserved for crops.';
    if (catalog.obstacles.some(([x,y]) => x === point.x && y === point.y)) return 'Rocks cannot hold a machine.';
  }
  const occupied = new Map();
  for (const [name, point] of Object.entries(withPositions(definitions, positions))) {
    const key = `${point.x},${point.y}`;
    if (occupied.has(key)) return `Pad occupied by ${occupied.get(key)}. Uninstalled recycling pads stay reserved.`;
    occupied.set(key, name);
  }
  const resolved=withPositions(definitions,positions);
  for(const [name,route] of Object.entries(state.conveyors?.routes||{})) {
    const rule=catalog.conveyors.routes[name],from=resolved[rule.source],to=resolved[rule.target];
    if(route.path[0]!==from.y*8+from.x || route.path.at(-1)!==to.y*8+to.x || route.path.slice(1,-1).some(cell=>occupied.has(`${cell%8},${Math.floor(cell/8)}`))) return 'Drain and remove connected conveyors before moving these machines.';
  }
  return null;
}

export function routeDistance(from, to, catalog) {
  const queue = [[from.x,from.y,0]], visited = new Set([`${from.x},${from.y}`]);
  for (let i=0; i<queue.length; i++) {
    const [x,y,d] = queue[i];
    if (x === to.x && y === to.y) return d;
    for (const [dx,dy] of [[1,0],[0,1],[-1,0],[0,-1]]) {
      const nx=x+dx, ny=y+dy, key=`${nx},${ny}`;
      if (nx < 0 || nx > 7 || ny < 0 || ny > 7 || visited.has(key) || catalog.obstacles.some(([ox,oy]) => ox === nx && oy === ny)) continue;
      visited.add(key); queue.push([nx,ny,d+1]);
    }
  }
  return null;
}

export function routeCosts(state, catalog, positions) {
  const entities = layoutEntities(state,catalog,positions);
  const pairs = [['chest','mill'],['mill','oven'],['oven','depot']];
  if (state.recycling) pairs.push(['well','composter'],['composter','mixer'],['mixer','well']);
  return pairs.map(([from,to]) => ({from,to,moves:routeDistance(entities[from],entities[to],catalog)}));
}

export function compactPositions(state, catalog) {
  return Object.fromEntries(Object.entries(catalog.layout.compact).filter(([name]) => !['composter','mixer'].includes(name) || state.recycling));
}
