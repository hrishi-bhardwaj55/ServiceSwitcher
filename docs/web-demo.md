# Web demo and evidence viewer

The C15 interface is a four-screen, read-mostly explanation of one measured audit.
It is deliberately separate from authentication, account management, billing, and
settings, which are outside the v1 scope.

## Run it

```bash
npm ci --prefix apps/web
npm --prefix apps/web run dev
```

Open `http://localhost:3000`. The quickest demonstration is **Tax projection
error** → **Start audit** → **View completed demo now** → **Open evidence**.

## Screen contract

1. **Demo picker** offers clean, tax-projection, escrow-transfer, and legitimate
   reassessment scenarios. A custom path accepts up to five PDF files of at most
   10 MB each.
2. **Processing** exposes the seven bounded graph stages and current status. It
   never renders prompts, hidden reasoning, or server traces.
3. **Dashboard** separates deterministic payment arithmetic from the finding. It
   shows before/after components, potential impact, monthly change, severity, and
   the number of documents checked.
4. **Finding detail** renders the real synthetic PDF page, overlays the cited value
   using normalized page coordinates, links the original PDF and primary guidance,
   and supplies an editable draft that the user must copy and send themselves.

The two committed PNGs under `apps/web/public/demo/` are deterministic 2× renders
of the adjacent committed PDFs. They are browser display derivatives, not substitute
evidence. The original PDFs are marked synthetic on-page and are always linked from
the viewer.

## Privacy and scope

Custom PDFs are retained only as browser `File` objects for the current page
session. They are not uploaded or persisted. Because the C15 interface does not
invent structured account history for those files, it explicitly identifies the
dashboard as the measured synthetic demonstration instead of presenting its numbers
as a custom-file result.

This is audit information, not a legal conclusion. The UI uses cautious language,
links relevant sources, never sends the action draft, and keeps the user in control.

## Verification

```bash
npm --prefix apps/web run typecheck
npm --prefix apps/web test
npm --prefix apps/web run build
npx --prefix apps/web playwright install chromium
npm --prefix apps/web run test:e2e
```

The component suite covers the payment decomposition and evidence selection and
highlight. The Playwright test walks the public path from scenario selection through
the processing screen, dashboard, alternate source document, and editable draft.
The layout was also inspected manually at desktop and 390×844 phone viewports with
no console warnings or errors.
