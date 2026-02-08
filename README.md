# The Learning Curve

A multi-page, interactive B2B/B2C training website with an immersive starfield background, animated metrics, and client-side cart/checkout.

## Local Preview

From the `the-learning-curve` folder:

```bash
python3 -m http.server 8000
```

Then open `http://localhost:8000`.

## Deploy

This is a static site. You can deploy it with:

- GitHub Pages
- Netlify
- Vercel (static)

Point the deployment root at the `the-learning-curve` folder.

## n8n CRM Webhook

Set your n8n webhook URL in `the-learning-curve/assets/js/config.js` to receive contact and checkout submissions.
