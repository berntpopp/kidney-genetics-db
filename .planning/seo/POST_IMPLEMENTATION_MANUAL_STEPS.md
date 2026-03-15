# SEO Post-Implementation Manual Steps

> These steps require manual action (external services, domain verification, etc.)
> and cannot be automated in the codebase.

## 1. Google Search Console Setup

**Priority: Critical — do this first**

1. Go to https://search.google.com/search-console
2. Add property `https://kidney-genetics.org`
3. Verify domain ownership via DNS TXT record:
   - Add a TXT record to your DNS: `google-site-verification=<code>`
   - Alternative: upload HTML verification file to `frontend/public/`
4. Submit sitemap: `https://kidney-genetics.org/sitemap.xml`
5. Request indexing of key pages:
   - `/` (Home)
   - `/genes` (Gene Browser)
   - `/about` (About)
6. Monitor the "Coverage" and "Performance" reports weekly for the first month

**Expected timeline**: Pages start appearing in Google within 1-4 weeks.

## 2. Database Registry Submissions

**Priority: Medium — do within 30 days**

Submit KGDB to these registries for backlinks and discoverability:

| Registry | URL | What to submit |
|----------|-----|----------------|
| re3data.org | https://www.re3data.org/suggest | KGDB as a research data repository |
| FAIRsharing.org | https://fairsharing.org/new | KGDB as a database resource |
| bio.tools | https://bio.tools/register | KGDB as a bioinformatics tool |
| dkNET | https://dknet.org/about/submission | KGDB as an NIDDK resource |
| BioSchemas.org | https://bioschemas.org/developer/liveDeploys | Register as BioSchemas adopter |

**For each submission, include:**
- Name: Kidney Genetics Database (KGDB)
- URL: https://kidney-genetics.org
- Description: Evidence-based kidney disease gene curation with multi-source integration. Curated nephrology gene panel and renal genetics resource from PanelApp, ClinGen, GenCC, HPO, and more.
- License: CC BY 4.0
- Keywords: kidney genetics, nephrology, genomics, gene curation, kidney disease
- Contact: (your email)

## 3. Structured Data Validation

**Priority: High — do after first deployment**

1. **Google Rich Results Test**: https://search.google.com/test/rich-results
   - Test: `https://kidney-genetics.org/`
   - Test: `https://kidney-genetics.org/genes/PKD1`
   - Note: Google's validator does NOT understand BioSchemas `Gene` type — expect warnings for unknown type. This is expected.

2. **Schema.org Markup Validator**: https://validator.schema.org/
   - Validates general Schema.org compliance
   - Test all page types

3. **BioSchemas Validator**: https://bioschemas.org/tutorials/howto/howto_check_deploy
   - Use the Heriot-Watt BioSchemas scraper for BioSchemas-specific validation
   - Verifies Gene 1.0-RELEASE profile compliance

## 4. Social Media Preview Testing

**Priority: Medium — do after first deployment**

Test that OG images and meta tags render correctly:

1. **Facebook Sharing Debugger**: https://developers.facebook.com/tools/debug/
   - Enter: `https://kidney-genetics.org/`
   - Enter: `https://kidney-genetics.org/genes/PKD1`
   - Click "Scrape Again" to refresh cache

2. **Twitter/X Card Validator**: https://cards-dev.twitter.com/validator
   - Test the same URLs

3. **LinkedIn Post Inspector**: https://www.linkedin.com/post-inspector/
   - Test sharing preview

## 5. Academic Backlink Strategy

**Priority: Low — ongoing**

1. **Publish full database paper** in NAR Database Issue, Bioinformatics, or Human Mutation
   - The NDT abstract (#787) exists — expand to full paper
   - This generates the highest-value backlinks in bioinformatics

2. **Contact data source partners** for cross-linking:
   - ClinGen Kidney Working Groups
   - Genomics England PanelApp team
   - GenCC consortium
   - HPO team

3. **Submit to NIDDK** Kidney Genetics & Genomics program page as a community resource

## 6. Monitoring Checklist (Monthly)

- [ ] Check Google Search Console for crawl errors
- [ ] Review indexing coverage (target: 5,000+ pages indexed)
- [ ] Monitor keyword rankings for target terms
- [ ] Check Core Web Vitals in Search Console
- [ ] Verify structured data errors/warnings
- [ ] Run Lighthouse audit (`make lighthouse`)
