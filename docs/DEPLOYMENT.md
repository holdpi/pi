# HoldPI website deployment

The published site at [holdpi.com](https://holdpi.com) is a static GitHub Pages build from [noirchain/holdpi-site](https://github.com/noirchain/holdpi-site). The deployed baseline is revision `aa558c61233ec750b1710db02d49a0c2372cc515`. The audit repository carries the subsequent maintainability changes and regenerated review exports in `website/`. Publishing that audit revision to the site is a separate release step.

For local review, use `node scripts/serve.mjs` and open `/docs`, `/protocol` and `/brandbook`. The preview server listens on loopback. The optional `PI_REVIEW_KEY_FILE` points to an owner-local file for protected preview hosting behind HTTPS. The public site's client-side gate provides presentation only. Auditor repository access is handled through GitHub.

To reproduce the Pages tree in a separate directory, run:

```sh
python3 scripts/stage-github-pages.py /path/to/empty/pages-staging
```

The script adds `.nojekyll`, the custom-domain file and directory routes for `/docs/`, `/protocol/` and `/brandbook/`. The command writes locally. The standby static Netlify configuration is included in `netlify.toml`.

Both review ZIPs are regenerated from the source and passing test receipt in this audit checkout so a fresh clone can exercise the browser export path. Their provenance and build inputs are described in [Verification](../audit/VERIFICATION.md). Website hosting and any future on-chain registration are independent.
