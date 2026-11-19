// Add published content here. Empty arrays deliberately show no fabricated posts.
// Review: {slug, artist, album, year, genre, published, cover, scores:{composition,writing,performance,production,intangibles}, body:[paragraphs]}
// Article: {slug,title,published,description,hero,body:[paragraphs]}
// Ranking: {slug,title,published,updated,description,featured,hero,body:[paragraphs]}
export const reviews = [];
export const articles = [];
export const rankings = [];
export const scoreFor = (scores) => Math.round(Object.values(scores).reduce((a,b)=>a+b,0)/5*10)/10;
export const dateLabel = (iso) => new Date(`${iso}T12:00:00Z`).toLocaleDateString('en-US',{year:'numeric',month:'long',day:'numeric',timeZone:'UTC'});
