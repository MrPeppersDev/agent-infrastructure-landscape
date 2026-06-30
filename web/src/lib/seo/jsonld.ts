// JSON-LD schema builders. Return plain objects ready for JSON.stringify
// and emission inside a <script type="application/ld+json"> tag.
//
// Schemas chosen per Google's structured-data guidance:
//   - Dataset       — landing page, drives indexing in Google Dataset Search
//                     (a separate ranking surface from web search)
//   - Article       — finding sub-pages, makes each citable
//   - ItemList      — leaderboards and lineages
//   - SoftwareApplication — system detail pages

import { SITE_NAME, SITE_DESCRIPTION, absoluteUrl } from '$lib/site';

const REPO_URL = 'https://github.com/MrPeppersDev/agent-infrastructure-landscape';

export function datasetLd(opts: {
  recordCount: number;
  edgeCount: number;
  modifiedDate?: string;
}): object {
  return {
    '@context': 'https://schema.org',
    '@type': 'Dataset',
    name: SITE_NAME,
    description: `${SITE_DESCRIPTION} ${opts.recordCount} systems, ${opts.edgeCount} typed edges.`,
    url: absoluteUrl('/'),
    license: 'https://creativecommons.org/licenses/by/4.0/',
    creator: {
      '@type': 'Organization',
      name: 'AI Agent Infrastructure Landscape contributors',
      url: REPO_URL
    },
    distribution: [
      {
        '@type': 'DataDownload',
        contentUrl: `${REPO_URL}/raw/main/data/landscape.json`,
        encodingFormat: 'application/json'
      },
      {
        '@type': 'DataDownload',
        contentUrl: `${REPO_URL}/raw/main/data/landscape.edges.json`,
        encodingFormat: 'application/json'
      }
    ],
    keywords: [
      'AI agent memory',
      'agent infrastructure',
      'memory systems',
      'LLM memory',
      'agent memory comparison',
      'LangChain memory',
      'Mem0',
      'Letta',
      'Zep'
    ],
    ...(opts.modifiedDate ? { dateModified: opts.modifiedDate } : {})
  };
}

export function articleLd(opts: {
  headline: string;
  description: string;
  url: string;
  datePublished?: string;
}): object {
  return {
    '@context': 'https://schema.org',
    '@type': 'Article',
    headline: opts.headline,
    description: opts.description,
    url: opts.url,
    publisher: {
      '@type': 'Organization',
      name: SITE_NAME,
      url: absoluteUrl('/')
    },
    ...(opts.datePublished ? { datePublished: opts.datePublished } : {})
  };
}

export function itemListLd(opts: {
  name: string;
  items: { name: string; url: string }[];
}): object {
  return {
    '@context': 'https://schema.org',
    '@type': 'ItemList',
    name: opts.name,
    itemListElement: opts.items.map((item, i) => ({
      '@type': 'ListItem',
      position: i + 1,
      name: item.name,
      url: item.url
    }))
  };
}

export function breadcrumbLd(opts: {
  /** Crumbs in display order — first is the root, last is the current page. */
  items: { name: string; url: string }[];
}): object {
  return {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: opts.items.map((item, i) => ({
      '@type': 'ListItem',
      position: i + 1,
      name: item.name,
      item: item.url
    }))
  };
}

export function faqLd(opts: {
  qas: { question: string; answer: string }[];
}): object {
  return {
    '@context': 'https://schema.org',
    '@type': 'FAQPage',
    mainEntity: opts.qas.map((qa) => ({
      '@type': 'Question',
      name: qa.question,
      acceptedAnswer: {
        '@type': 'Answer',
        text: qa.answer
      }
    }))
  };
}

export function softwareLd(opts: {
  name: string;
  description: string;
  url: string;
  category?: string;
}): object {
  return {
    '@context': 'https://schema.org',
    '@type': 'SoftwareApplication',
    name: opts.name,
    description: opts.description,
    url: opts.url,
    applicationCategory: opts.category ?? 'DeveloperApplication',
    operatingSystem: 'any'
  };
}
