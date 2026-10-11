const BUSINESS_EMAIL = "{{BUSINESS_EMAIL}}";

export default function PrivacyPolicy() {
  return (
    <main style={{ maxWidth: 760, margin: "4rem auto", padding: "0 1.5rem", fontFamily: "system-ui, sans-serif", lineHeight: 1.6 }}>
      <h1>Glacier FDA Listing privacy policy</h1>
      <p>Last updated: October 11, 2026</p>
      <p>Glacier FDA Listing reads Shopify product catalog information to prepare cosmetic listing review packets. It requests only read_products access and does not write to Shopify products, orders, customers, or other store records.</p>
      <h2>Data we process</h2>
      <p>We read product IDs, titles, handles, product types, tags, and the optional custom ingredients metafield. The responsible person may submit product label details, ingredient order, facility information, exemption answers, contact details, dates, and an ingredient-label file to generate a packet.</p>
      <h2>Use and storage</h2>
      <p>Shopify catalog data and packet form inputs are processed only to prepare the requested packet. Form inputs and uploaded labels are handled in a temporary workspace and removed when that request finishes. We do not retain product records, uploaded labels, or packet copies. Shopify OAuth session data (including Shopify user identifiers, names or email addresses where supplied, and access tokens) is stored in the app's session database to keep the embedded app connected; access is restricted to the app server. We do not sell data, use it for advertising, or share it with third parties.</p>
      <h2>Retention and deletion</h2>
      <p>Temporary packet inputs are deleted at the end of each request. On app uninstall, Shopify session records are deleted. We respond to Shopify customer data requests, customer redaction requests, and shop redaction requests. No customer data is read or stored by this app.</p>
      <h2>Contact</h2>
      <p>For privacy questions, contact <a href={`mailto:${BUSINESS_EMAIL}`}>{BUSINESS_EMAIL}</a>.</p>
    </main>
  );
}
