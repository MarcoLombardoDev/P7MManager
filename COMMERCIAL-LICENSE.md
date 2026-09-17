# Commercial Licence — P7M Manager

**P7M Manager — inspect signed .p7m containers and extract what they carry**  
Copyright © 2026 Marco Lombardo

P7M Manager is dual-licensed. It is available under the
[GNU Affero General Public License v3.0](LICENSE) at no cost, and under the commercial
terms in this document for those who cannot accept the AGPL's obligations.

Both licences cover **the same software**. There is no crippled edition, no feature held
back behind a paywall, no licence key and no phone-home. What you buy is **permission**,
not functionality.

That includes every capability: signature inspection, certificate details, integrity and
RSA signature checks, single-file and whole-folder queues, nested and base64 containers,
extraction with mirrored folder structures, and the CSV and JSON reports. Nothing is
reserved for a paid tier, now or later.

> **To buy, or to ask anything commercial — including whether you need this at all —
> email [marco.lombardo@gmail.com](mailto:marco.lombardo@gmail.com?subject=P7M%20Manager%20commercial%20licence%20enquiry).**
> Email is the only commercial channel: quotes, contracts, invoicing and pre-sales
> questions all go there. GitHub Issues are for bugs and feature requests.

> This page is a **commercial offer and a summary of terms**, not the signed agreement.
> The binding contract is the licence certificate issued per customer. It is not legal
> advice; have your own counsel review it before signing.

---

## 1. Do you actually need this?

Most people do not. Read this before reading the price list.

| What you want to do | Licence you need |
|---|---|
| Use P7M Manager inside your organisation, however many people, however many machines | **AGPL — free.** Nothing to buy, nothing to declare. |
| Process your own signed documents, in any volume, including regulated ones | **AGPL — free.** |
| Modify it for your own internal use and keep the changes to yourself | **AGPL — free.** |
| Publish a fork, or ship a modified version to someone else | **AGPL — free**, provided you release your modified source under AGPL-3.0. |
| Run a modified P7M Manager as a closed-source internal tool, for your own staff only | **Commercial** — see §3 |
| Ship P7M Manager, or code derived from it, inside a **closed-source product** you distribute | **Redistribution** — see §4 |
| Put its engine behind a **hosted or SaaS service for your customers**, without publishing your source | **Redistribution** |
| Redistribute it to your customers under **your own name or branding** | **Redistribution** |
| Your organisation's policy forbids AGPL code, and you need it in writing | **Commercial** (or **Redistribution**, if you also distribute) |

**Internal use is free, permanently, for organisations of any size.** Anyone telling you
otherwise about an AGPL project is mistaken. Buy a commercial licence when the AGPL's
*distribution* terms are the problem — not simply because you are a company.

The dividing line is one rule: **AGPL-3.0 is free as long as the source stays open.**

---

## 2. Licence structure

```
PRODUCT LICENSING
│
├── Community
│   └── AGPL-3.0
│
├── Commercial                    (internal use)
│   ├── Small       — 1–49 employees
│   ├── Medium      — 50–249 employees
│   ├── Large       — 250–999 employees
│   └── Enterprise  — 1,000+ employees / Corporate Group
│
└── Redistribution                (reaches third parties)
    ├── Standard
    └── Enterprise
```

Three kinds of licence, not six price points on one list:

- **Community** — the AGPL-3.0 build. Free, unlimited, internal use of any size.
- **Commercial** — removes the AGPL's copyleft obligation for **closed-source internal
  use**. Sized by the licensee's employee count. See §3.
- **Redistribution** — grants the right to **ship P7M Manager, or a derivative of it, to
  third parties** — embedded, OEM'd, resold, or offered as a service to your own
  customers. See §4. It is a different kind of licence from Commercial, not a bigger
  version of it: a five-person software house redistributing a product to ten thousand
  customers needs Redistribution, not a large Commercial tier.

Every tier, in every branch, is the **same software** under the opening of this document:
no feature is gated behind a higher tier.

---

## 3. What the Commercial licence grants

Subject to payment and to the tier purchased, a non-exclusive, non-transferable licence,
for **one named legal entity**, to:

1. use, copy and modify P7M Manager;
2. deploy it as an internal, closed-source tool, without publishing your modified source;
3. run it as an internally-accessed network service without triggering AGPL section 13,
   provided access is limited to your own authorised users and installations.

It does **not** automatically include, at any Commercial tier:

- redistribution to third parties, in any form;
- OEM or embedding in a product you ship;
- sublicensing;
- use by other companies in the same corporate group, unless the Enterprise tier's
  group-wide scope has been explicitly agreed and named in the certificate.

Any of those needs a **Redistribution licence** instead of, or alongside, Commercial — see
§4.

### 3.1 The four Commercial tiers

| Tier | Employees | |
|---|---|---|
| **Small** | 1–49 | One legal entity, internal use, non-redistributable. |
| **Medium** | 50–249 | The same model, applied to a mid-sized organisation. |
| **Large** | 250–999 | The same model, applied to a larger organisation. |
| **Enterprise** | 1,000+, **or** any Corporate Group scope | Covers an organisation of 1,000+ employees, or one needing a group-wide perimeter. The certificate must state exactly which legal entities are included. |

Belonging to a large group does not, by itself, let a small subsidiary's Small-tier licence
cover the rest of the group. A group-wide perimeter is never implied — it must be
explicitly agreed and named entity by entity.

### 3.2 Employee count

Unless the applicable Enterprise / Group agreement states a different scope:

> Employee count refers to the total number of employees of the licensed legal entity.

It does **not** automatically include customers, end users, suppliers, partners, or
external consultants.

### 3.3 Corporate Group

A **Corporate Group** is a set of companies directly or indirectly controlled by the same
parent company, or otherwise part of the same corporate structure, as defined in the
applicable agreement. Membership in a group is not, by itself, authorisation for the group.

---

## 4. What the Redistribution licence grants

A **Redistribution licence** is required whenever P7M Manager, or any part of it — the
interface or the parsing engine alike — is passed on to a third party, regardless of
organisation size. Examples:

- incorporation into another piece of software, including using `p7mmanager.core` as a
  signature-reading library inside your own product;
- embedding;
- distribution alongside a proprietary product;
- distribution to customers or to end users;
- commercialisation of a derivative product;
- OEM scenarios;
- offering the engine's output through a service you run for your customers.

Subject to payment and to the specific agreement, a Redistribution licence may grant:

1. modification, integration and embedding rights;
2. the right to distribute the result, in source or binary form, with no obligation to
   publish your own source;
3. the right to commercialise the resulting product;
4. sublicensing of these rights to your own end users, **solely as part of your product**,
   not as a standalone competing tool.

It does **not** automatically grant: exclusivity; unlimited sublicensing; rights to the
Project Owner's trademarks; rights to third-party dependencies (§11); or transfer of the
licence to another party.

### 4.1 Redistribution — Standard

For ordinary commercial redistribution: software houses, ISVs, integrators, document
management vendors and businesses embedding P7M Manager in a product, distributed to a
non-exceptional number of customers or installations.

### 4.2 Redistribution — Enterprise

For redistribution at scale: large software houses and groups, worldwide distribution,
high-volume products, large-scale platforms and large OEM programmes. Unlike Commercial,
this tier is **not** primarily sized by employee count: number of products, customers,
installations, end users, territory, revenue and support level are weighed per case in the
agreement.

---

## 5. Price list

All prices in **EUR, excluding VAT**, per **licensee organisation** — the legal entity and,
where the tier says so, the agreed group perimeter. Seats are never counted: you are not
billed per developer, per user or per installation.

| Tier | Price | Scope |
|---|---:|---|
| **Community** | **Free** | Everything P7M Manager does, under AGPL-3.0. Unlimited internal use. |
| **Commercial — Small** | **€600 / year** | 1–49 employees. Closed-source internal use, one legal entity. |
| **Commercial — Medium** | **€1,200 / year** | 50–249 employees. Same model as Small. |
| **Commercial — Large** | **€2,200 / year** | 250–999 employees. Same model as Small and Medium. |
| **Commercial — Enterprise** | **from €3,800 / year** | 1,000+ employees, or a group-wide perimeter. Written answers to procurement and legal questionnaires. |
| **Redistribution — Standard** | **€2,000 / year** | Ordinary commercial redistribution: embed it, or its engine, in a product you sell. |
| **Redistribution — Enterprise** | **from €7,000 / year** | Large-scale redistribution and OEM programmes. Scope priced per case. |

### Perpetual option

A perpetual licence is bought once and never renews. It covers **the major version current
at the date of purchase**, in perpetuity, together with every patch and minor release
within that major version. Moving to a later major version is a new purchase.

It is priced at **three times the annual rate** of the same tier, and is offered on the
four fixed-price tiers only — both Enterprise tiers are negotiated per case instead.

| Tier | Perpetual price (one-off) |
|---|---:|
| Commercial — Small | **€1,800** |
| Commercial — Medium | **€3,600** |
| Commercial — Large | **€6,600** |
| Redistribution — Standard | **€6,000** |

Support (§6) runs for **twelve months** from a perpetual purchase, and can be renewed
afterwards at 20% of the annual rate of the same tier. The licence itself does not expire
when support does.

### What every paid licence includes

- **Email support** — see §6. Always included, never sold separately to a paying customer.
- **Updates for the whole term.** Every version released while your subscription is active
  is licensed to you.
- **No retroactive charge.** Renewals are priced at the rate in force when you first
  bought, for as long as you renew without a gap.
- **Cancel any time.** No notice period, no auto-renewal trap.

### Discounts

| Who | What |
|---|---|
| Fewer than 10 employees **and** under €1M annual revenue | **50% off** any annual Commercial or Redistribution tier |
| Registered non-profits, accredited academic institutions, published research | **Free commercial licence** — ask |

---

## 6. Support

**Every paying customer gets support. It is included in the price, at every paid tier, and
it runs over email.**

| Tier | Support | Target first response |
|---|---|---|
| Community | GitHub Issues, best effort | — |
| Commercial — Small / Medium | Email | 5 business days |
| Commercial — Large | Email | 3 business days |
| Commercial — Enterprise | Email, private channel | 2 business days |
| Redistribution — Standard | Email | 3 business days |
| Redistribution — Enterprise | Email, private channel | 2 business days |

- **Included:** installation and configuration problems, questions about intended
  behaviour, diagnosis of suspected bugs, help with a container the tool cannot read, and
  licensing or compliance questions.
- **A response commitment, not a fix commitment.** Confirmed bugs are prioritised over new
  features, but no repair window is guaranteed at any tier.
- **Not included:** building your workflow for you, writing features, or operating the
  software on your behalf — see §7.

Support answers how the tool behaves. It does not constitute a legal opinion on whether a
given signature is valid; see §9 and the [README](README.md#what-this-tool-does-not-claim).

---

## 7. Custom development

Anything that changes the software for you — a new format, a connector, an integration
with a document management system, a bespoke build — is **never included in a licence
fee**, at any tier. It is quoted separately, per project:

1. You describe what you need.
2. You get a written scope, a fixed price and a delivery window before any work starts.
3. Nothing is invoiced until you accept that quote.

The indicative day rate is **€500 / day**, used to size a quote; the quote itself is
fixed-price, not time-and-materials.

- **A commercial licence is not required to commission work.** AGPL users can pay for
  custom development too.
- **By default the result is merged into the public project** under AGPL-3.0, which is why
  the rate is what it is. Exclusive or unpublished work is priced differently.

---

## 8. How to buy

1. **Ask.** Write to
   **[marco.lombardo@gmail.com](mailto:marco.lombardo@gmail.com?subject=P7M%20Manager%20commercial%20licence%20enquiry)**.
   Say what you intend to build, roughly how big your organisation is (for Commercial), or
   how the software will reach third parties (for Redistribution).
2. **Confirm the tier.** You get a written statement of which tier applies and why.
3. **Invoice.** Issued in EUR, payable by bank transfer within 30 days.
4. **Certificate.** On payment you receive a signed licence certificate naming your
   organisation, the tier, the term and the covered products. That certificate — not a key
   file — is the licence.

There is **no licence key, no activation, no phone-home.** The software behaves identically
whether or not you have paid. Compliance is contractual and self-declared; there is no
audit clause.

---

## 9. Term, warranty and liability

- **Term.** Annual from the invoice date, unless the certificate says otherwise, or
  perpetual where the perpetual option in §5 was purchased.
- **Updates.** Included for the duration of the term.
- **Warranty.** P7M Manager is provided **as is**. No warranty of merchantability, fitness
  for a particular purpose, or non-infringement.
- **No legal validation.** P7M Manager checks integrity, and for RSA the signature itself.
  It has no trust list, does not check revocation, and does not validate timestamps against
  an authority. **Nothing it reports is a legal validation of a signature**, at any tier,
  and no commercial agreement changes that. Where a legal determination is needed, use an
  accredited validation service.
- **Liability.** Total aggregate liability under a commercial licence is limited to **the
  fees paid in the twelve months preceding the claim**. Liability is not excluded where it
  cannot lawfully be excluded — death or personal injury caused by negligence, fraud, or
  wilful misconduct.
- **Indemnity.** No IP indemnity at Commercial Small/Medium/Large or Redistribution
  Standard. Both Enterprise tiers may include one; ask, and it will be stated in the
  certificate.
- **Governing law.** Italian law, courts of Milan, unless the certificate names otherwise.

---

## 10. What is *not* included

- **No SLA on the software itself.** Response targets are commitments about replying to
  you, not about fixing anything within a window.
- **No custom development.** Quoted separately — see §7.
- **No legal validation service**, and no certification of any signature. See §9.
- **No guarantee of future features.** The roadmap is not a contract.
- **No exclusivity.** The same licence is available to your competitors.
- **No rights to third-party components.** See §11.
- **No hosted service.** P7M Manager is a desktop application. There is nothing to sign
  into, and no document ever leaves the machine it is opened on.
- **No implied redistribution rights on a Commercial licence**, and no implied group-wide
  scope without an explicit Enterprise perimeter.

---

## 11. Third-party components

A commercial licence covers P7M Manager's own code. Everything it is built on is separately
licensed by its own authors, and this licence cannot and does not relicense any of it.

The dependency list is deliberately short, and that is a licensing decision as much as an
engineering one. **The engine has no third-party dependency at all**: the ASN.1, CMS and
X.509 readers under `p7mmanager/core/` are written against the standard library, so no
copyleft code sits underneath the part a redistributor is most likely to embed.

| Component | Licence | What it asks of you |
|---|---|---|
| Python, standard library | PSF-2.0 | Attribution. Nothing further. |
| PySide6 / shiboken6 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only | Under the LGPL option: ship the licence text, state that Qt is used, keep Qt replaceable by the recipient, and impose no further restriction on Qt itself. |
| PyInstaller (build only) | GPL-2.0-or-later **with the Bootloader Exception** | Nothing. The exception grants unlimited permission to embed the bootloader in a combined program and distribute it. |

The PyPI wheels for PySide6 *are* the open-source build of Qt; their metadata offers no
commercial option. A Qt commercial licence is bought from The Qt Company and is not
something this licence, or a wheel, can grant.

**A build is more than this table.** A frozen bundle contains the transitive closure of
everything those packages link — Qt's own libraries and plugins, and whatever the build
machine's linker resolved. Two consequences are worth stating because they bit Orion:

- The standard library's optional `readline` extension drags in a **GPL-3.0-or-later
  library with no linking exception**, which is the one combination a Redistribution tier
  cannot survive. `p7mmanager.spec` excludes it, and nothing in P7M Manager uses it.
- A redistributor must inventory what they actually ship, from the archives they build,
  and reproduce the notices each component requires.

These determinations were made from package metadata, are current as at the version of this
document, and are **not a legal opinion**. Verify them against the versions you ship.

---

## 12. Contributors

Contributions are accepted under the [Contributor License Agreement](CLA.md), which grants
the Project Owner the right to license contributed code under both AGPL-3.0 and commercial
terms. That grant is what makes dual licensing possible: without it, a single contributed
patch would block commercial licensing for everyone.

Contributors keep the copyright in their work, and receive a perpetual, royalty-free
commercial licence to P7M Manager for their own use, as thanks.

---

## 13. Contact

**Commercial licensing, quotes and support for paying customers:
[marco.lombardo@gmail.com](mailto:marco.lombardo@gmail.com?subject=P7M%20Manager%20commercial%20licence%20enquiry)**

For anything that is *not* a purchase — a bug, a feature request, a container the tool
cannot read, a question about which row of §1 you fall into — the
[issue tracker](https://github.com/MarcoLombardoDev/P7MManager/issues) is the better
channel, and the answer helps whoever asks next.

---

## 14. Terminology

This document uses **Community**, **Commercial** and **Redistribution** as the three
licence families. **OEM** is deliberately not a top-level category: it appears only as an
example, because it describes one *scenario* within Redistribution, not a distinct set of
rights —

> OEM, embedded and other redistribution scenarios are covered by the Redistribution
> Licence.

---

*This document is a commercial offer, not legal advice. Prices and terms may change for new
purchases; a licence already issued is governed by the certificate you hold, not by later
revisions of this file.*

*Copyright © 2026 Marco Lombardo. P7M Manager is licensed under AGPL-3.0; commercial
licensing is available under the terms above.*
