// Print only non-secret claims; never print the JWT or request token.
const url = new URL(process.env.ACTIONS_ID_TOKEN_REQUEST_URL);
url.searchParams.set('audience', 'sts.amazonaws.com');
const response = await fetch(url, {headers:{Authorization:`bearer ${process.env.ACTIONS_ID_TOKEN_REQUEST_TOKEN}`}});
if (!response.ok) throw new Error(`OIDC request failed: ${response.status}`);
const {value} = await response.json();
const claims = JSON.parse(Buffer.from(value.split('.')[1], 'base64url').toString('utf8'));
console.log(JSON.stringify({sub:claims.sub,aud:claims.aud,repository:claims.repository,repository_id:claims.repository_id,repository_owner_id:claims.repository_owner_id}, null, 2));
