// Evaluate the rules compiled by the shared Python robots parser.
export function robotsAllowed(url, rules) {
  const u=new URL(url);
  const resource=(u.pathname+u.search).replace(/%([0-9a-f]{2})/gi,(match,hex) => {
    const value=String.fromCharCode(parseInt(hex,16));
    return /^[A-Za-z0-9._~-]$/.test(value) ? value : '%'+hex.toUpperCase();
  });
  const matches=rules.filter(rule=>new RegExp(rule.pattern).test(resource));
  matches.sort((a,b)=>b.specificity-a.specificity || Number(b.allow)-Number(a.allow));
  return matches.length===0 || matches[0].allow;
}
