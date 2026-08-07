// api/proxy.js
export const config = {
  runtime: 'edge',
};

export default async function handler(req) {
  const corsHeaders = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, HEAD, OPTIONS',
    'Access-Control-Allow-Headers': '*',
  };

  if (req.method === 'OPTIONS') {
    return new Response(null, { status: 204, headers: corsHeaders });
  }

  const { searchParams } = new URL(req.url);
  const targetUrl = searchParams.get('url');
  const apiPassword = searchParams.get('api_password');

  if (apiPassword !== 'Milito22.') {
    return new Response('Yetkisiz erisim.', { status: 403, headers: corsHeaders });
  }

  if (!targetUrl) {
    return new Response('Eksik "url" parametresi.', { status: 400, headers: corsHeaders });
  }

  try {
    let finalMediaUrl = targetUrl;

    if (targetUrl.includes('watch.php') || targetUrl.includes('dlhd.pk')) {
      const matchId = targetUrl.match(/id=(\d+)/);
      const channelId = matchId ? matchId[1] : null;

      if (channelId) {
        const lookupUrl = `https://newembedplay.xyz/server_lookup.php?channel_id=premium${channelId}`;
        const lookupRes = await fetch(lookupUrl, {
          headers: {
            'Referer': `https://newembedplay.xyz/premiumtv/daddylivehd.php?id=${channelId}`,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
          }
        });

        if (lookupRes.ok) {
          const keyData = await lookupRes.json();
          if (keyData && keyData.server_key) {
            const serverKey = keyData.server_key;
            finalMediaUrl = `https://${serverKey}new.newkso.ru/${serverKey}/premium${channelId}/mono.m3u8`;
          }
        }
      }
    }

    const response = await fetch(finalMediaUrl, {
      method: req.method,
      headers: {
        'Referer': 'https://forcedtoplay.xyz/',
        'Origin': 'https://forcedtoplay.xyz',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
        'Accept': '*/*',
      },
    });

    const newHeaders = new Headers(response.headers);
    Object.entries(corsHeaders).forEach(([k, v]) => newHeaders.set(k, v));

    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: newHeaders,
    });

  } catch (err) {
    return new Response('Proxy Baglanti Hatasi: ' + err.message, { status: 500, headers: corsHeaders });
  }
}
