# HoldPI website deployment

The published site at [holdpi.com](https://holdpi.com) is a static GitHub Pages build from [noirchain/holdpi-site](https://github.com/noirchain/holdpi-site). Its source snapshot is in `website/`. The audit repository is prepared separately from the publishing repository.

For local review, use `node scripts/serve.mjs` and open `/docs`, `/protocol` and `/brandbook`. The preview server listens on loopback. The optional `PI_REVIEW_KEY_FILE` points to an owner-local file for protected preview hosting behind HTTPS. The public site's client-side gate provides presentation only. Auditor repository access is handled through GitHub.

To reproduce the Pages tree in a separate directory, run:

```sh
python3 scripts/stage-github-pages.py /path/to/empty/pages-staging
```

The script adds `.nojekyll`, the custom-domain file and directory routes for `/docs/`, `/protocol/` and `/brandbook/`. The command writes locally. The standby static Netlify configuration is included in `netlify.toml`.

Both public review ZIP files are included as served so a fresh clone can test the exact browser export path. Their provenance and build inputs are described in [Verification](../audit/VERIFICATION.md). Website hosting and any future on-chain registration are independent.
