<template>
  <!--
    Prerendered to /app-shell/index.html, the nginx fallback for client-only routes
    (/genes/:symbol, /curation, ...): header and footer with an empty main, so a deep link
    never paints another page's content first. Never give this route noindex or a
    canonical: crawlers read this HTML for every gene page.
  -->
  <div aria-busy="true" />
</template>
