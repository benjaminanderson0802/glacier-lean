import { useEffect } from "react";
import type { ActionFunctionArgs, HeadersFunction, LoaderFunctionArgs } from "react-router";
import { Form, useActionData, useLoaderData, useNavigation } from "react-router";
import { authenticate } from "../shopify.server";
import { boundary } from "@shopify/shopify-app-react-router/server";
import { createComplianceReport } from "../models/cosmetics.server.mjs";
import { createSubscriptionRequest, getActiveSubscription, productLimitForSubscription } from "../models/billing.server.mjs";
import { PLANS } from "../models/plans.mjs";
import { prepareFdaPacket } from "../models/fda-packet.server.mjs";
import { getDemoReport, isLocalFixtureRequest } from "../models/demo-fixture.server.mjs";

const runGraphql = async (admin: any, query: string, options?: object) => {
  const response = await admin.graphql(query, options);
  return response.json();
};

export const loader = async ({ request }: LoaderFunctionArgs) => {
  if (isLocalFixtureRequest(request)) {
    const demoResult = new URL(request.url).searchParams.get("result") === "uncertain" ? {
      result: "uncertain — please check",
      customer_must_submit: true,
      submitted: false,
      signed: false,
      please_confirm: ["ingredient label/source document", "responsible person confirmation", "facility FEI or exemption", "product category"],
    } : null;
    return { report: await getDemoReport(), subscriptions: [], demo: true, demoResult };
  }
  const { admin } = await authenticate.admin(request);
  const [report, subscriptions] = await Promise.all([
    createComplianceReport((query, options) => runGraphql(admin, query, options)),
    getActiveSubscription((query) => runGraphql(admin, query)),
  ]);
  return { report, subscriptions, demo: false, demoResult: null };
};

export const action = async ({ request }: ActionFunctionArgs) => {
  if (isLocalFixtureRequest(request)) {
    return { result: {
      result: "uncertain — please check",
      customer_must_submit: true,
      submitted: false,
      signed: false,
      please_confirm: ["ingredient label/source document", "responsible person confirmation", "facility FEI or exemption", "product category"],
    } };
  }
  const { admin } = await authenticate.admin(request);
  const form = await request.formData();
  if (form.get("intent") === "subscribe") {
    const plan = String(form.get("plan") || "");
    const appUrl = process.env.SHOPIFY_APP_URL;
    if (!appUrl) return { error: "App URL is not configured yet." };
    const billing = await createSubscriptionRequest(
      (query, options) => runGraphql(admin, query, options),
      { plan, returnUrl: `${appUrl}/app?billing=confirmed`, test: process.env.SHOPIFY_BILLING_TEST !== "false" },
    );
    if (!billing.confirmationUrl) return { error: "Shopify did not return a billing approval link." };
    return { billingConfirmationUrl: billing.confirmationUrl };
  }

  if (form.get("intent") !== "prepare") return { error: "Choose an action to continue." };
  const productId = String(form.get("product_id") || "");
  const [report, subscriptions] = await Promise.all([
    createComplianceReport((query, options) => runGraphql(admin, query, options)),
    getActiveSubscription((query) => runGraphql(admin, query)),
  ]);
  const product = report.products.find((item) => item.id === productId);
  if (!product) return { error: "That product is no longer in the Shopify catalog. Refresh and try again." };
  const productLimit = productLimitForSubscription(subscriptions[0]);
  if (!productLimit) return { error: "Choose a paid plan with Shopify before preparing packets." };
  if (report.hasMoreProducts) return { error: "This catalog exceeds the 250-product limit. No products were changed." };
  if (report.products.length > productLimit) return { error: `This plan supports up to ${productLimit} products. Change plans with Shopify to review this catalog.` };

  const file = form.get("label");
  if (!(file instanceof File)) return { error: "Upload the product's current ingredient label." };
  try {
    const rawIngredients = String(form.get("ingredients") || "");
    const ingredients = rawIngredients.split(/[,;\n]+/).map((part) => part.trim()).filter(Boolean);
    const categoryCodes = String(form.get("product_category_codes") || "").split(/[,;\s]+/).map((part) => part.trim()).filter(Boolean);
    const fei = String(form.get("facility_fei") || "").trim();
    const facilityName = String(form.get("facility_name") || "").trim();
    const exemptConfirmed = form.get("facility_exempt") === "yes" && form.get("customer_confirmed") === "yes";
    const payload = {
      shopify_id: product.id,
      shopify_title: product.title,
      responsible_person_name: String(form.get("responsible_person_name") || "").trim(),
      responsible_person_phone: String(form.get("responsible_person_phone") || "").trim(),
      responsible_person_role: String(form.get("responsible_person_role") || ""),
      product_category_codes: categoryCodes,
      product_name: String(form.get("product_name") || "").trim(),
      fragrance_or_flavor: String(form.get("fragrance_or_flavor") || "").split(",").map((part) => part.trim()).filter(Boolean),
      facility_fei: fei ? [fei] : [],
      facility_exempt: exemptConfirmed,
      facility_exemption_confirmed: exemptConfirmed,
      facilities: [{ fei, name: facilityName, exempt_confirmed: exemptConfirmed }],
      ingredients,
      exemption_checklist: {
        small_business: form.get("small_business") === "yes",
        product_may_be_covered_exception: form.get("covered_exception") === "yes",
        customer_wants_listing: form.get("customer_wants_listing") === "yes",
      },
      first_market_date: String(form.get("first_market_date") || "").trim(),
      last_listing_date: String(form.get("last_listing_date") || "").trim(),
      customer_confirmed: form.get("customer_confirmed") === "yes",
    };
    const result = await prepareFdaPacket(payload, {
      bytes: Buffer.from(await file.arrayBuffer()),
      type: file.type,
      name: file.name,
    });
    if (result.packetZip?.bytes) {
      result.packetZip.base64 = result.packetZip.bytes.toString("base64");
      delete result.packetZip.bytes;
    }
    return { result };
  } catch (error) {
    return { error: error instanceof Error ? error.message : "The packet could not be prepared." };
  }
};

export default function CosmeticsHome() {
  const { report, subscriptions, demo, demoResult } = useLoaderData<typeof loader>();
  const actionData = useActionData<typeof action>();
  const navigation = useNavigation();
  const busy = navigation.state !== "idle";
  const packetResult = actionData?.result ?? demoResult;
  const selectedPlan = subscriptions[0]?.name?.toLowerCase().includes("studio") ? "studio" : "starter";
  useEffect(() => {
    if (actionData && "billingConfirmationUrl" in actionData && actionData.billingConfirmationUrl) {
      window.open(actionData.billingConfirmationUrl, "_top");
    }
  }, [actionData]);

  return (
    <s-page heading="Glacier FDA Listing">
      <s-section heading="Read-only Shopify catalog">
        <s-paragraph>Review product details and prepare an FDA listing packet. Shopify product records are read only.</s-paragraph>
        {demo && <s-banner tone="info">Fixture preview only · no Shopify account or store data is connected.</s-banner>}
        <s-paragraph>{report.products.length} product{report.products.length === 1 ? "" : "s"} read · no Shopify changes made</s-paragraph>
        {report.hasMoreProducts && <s-banner tone="warning">The catalog contains more than 250 products. This app currently supports up to 250 products per store.</s-banner>}
        {report.products.length === 0 ? <s-paragraph>No products were found. Add products to Shopify, then refresh this page.</s-paragraph> : (
          <s-table>
            <s-table-header-row>
              <s-table-header>Product</s-table-header>
              <s-table-header>Shopify type</s-table-header>
              <s-table-header>Catalog source</s-table-header>
              <s-table-header>Review</s-table-header>
            </s-table-header-row>
            <s-table-body>
              {report.products.map((product) => (
                <s-table-row key={product.id}>
                  <s-table-cell>{product.title}</s-table-cell>
                  <s-table-cell>{product.catalogProductType || "Not set"}</s-table-cell>
                  <s-table-cell>{product.source}</s-table-cell>
                  <s-table-cell>{product.result}</s-table-cell>
                </s-table-row>
              ))}
            </s-table-body>
          </s-table>
        )}
      </s-section>

      <s-section heading="Prepare a product packet">
        <s-paragraph>Shopify catalog data cannot confirm label ingredients, FDA category, facilities, dates, or exemptions. Provide brand-confirmed details and upload the current label. Uncertain records do not produce an SPL file.</s-paragraph>
        <Form method="post" encType="multipart/form-data">
          <input type="hidden" name="intent" value="prepare" />
          <s-select name="product_id" label="Shopify product" required>
            {report.products.map((product) => <s-option key={product.id} value={product.id}>{product.title}</s-option>)}
          </s-select>
          <s-text-field name="product_name" label="Product name as printed on label" required></s-text-field>
          <s-text-field name="product_category_codes" label="FDA product category codes, separated by commas" required></s-text-field>
          <s-text-field name="ingredients" label="Ingredients in label order, separated by commas" required></s-text-field>
          <label className="file-field">Current ingredient label <input name="label" type="file" accept=".pdf,.png,.jpg,.jpeg,.txt,application/pdf,image/png,image/jpeg,text/plain" required /></label>
          <s-text-field name="responsible_person_name" label="Responsible person legal name" required></s-text-field>
          <s-text-field name="responsible_person_phone" label="Responsible person phone" required></s-text-field>
          <s-select name="responsible_person_role" label="Responsible person role" required>
            <s-option value="manufacturer">Manufacturer</s-option><s-option value="packer">Packer</s-option><s-option value="distributor">Distributor</s-option>
          </s-select>
          <s-text-field name="facility_fei" label="Facility FEI (if available)"></s-text-field>
          <s-text-field name="facility_name" label="Facility name (for a confirmed small-business exemption)"></s-text-field>
          <s-text-field name="fragrance_or_flavor" label="Fragrance or flavor, if present"></s-text-field>
          <s-text-field name="first_market_date" label="First marketed date (YYYY-MM-DD)" required></s-text-field>
          <s-text-field name="last_listing_date" label="Last FDA listing date (YYYY-MM-DD), if any"></s-text-field>
          <s-select name="small_business" label="Is this business eligible for the small-business exemption?" required>
            <s-option value="no">No</s-option><s-option value="yes">Yes, confirmed by responsible person</s-option>
          </s-select>
          <s-select name="covered_exception" label="Does a product meet an exception to the small-business exemption?" required>
            <s-option value="no">No</s-option><s-option value="yes">Yes, confirmed by responsible person</s-option>
          </s-select>
          <s-select name="facility_exempt" label="Is the facility exemption confirmed by the responsible person?" required>
            <s-option value="no">No</s-option><s-option value="yes">Yes</s-option>
          </s-select>
          <s-select name="customer_wants_listing" label="Should this product be included in the listing?" required>
            <s-option value="no">No</s-option><s-option value="yes">Yes, confirmed</s-option>
          </s-select>
          <s-select name="customer_confirmed" label="Have you reviewed and confirmed all supplied details?" required>
            <s-option value="no">No</s-option><s-option value="yes">Yes, I confirm these details</s-option>
          </s-select>
          <s-button type="submit" variant="primary" {...(busy ? { loading: true } : {})} disabled={report.products.length === 0 || busy}>Prepare review packet</s-button>
        </Form>
      </s-section>

      {actionData?.error && <s-banner tone="critical">{actionData.error}</s-banner>}
      {packetResult && <s-section heading="Packet review result">
        <s-banner tone={packetResult.result === "match" ? "success" : "warning"}>{packetResult.result}</s-banner>
        <s-paragraph>Every field remains source-linked. {packetResult.customer_must_submit ? "The responsible person must review, sign where required, and submit through FDA Cosmetics Direct." : "Review the items below before continuing."}</s-paragraph>
        {packetResult.please_confirm?.length > 0 && <s-unordered-list>{packetResult.please_confirm.map((item: string) => <s-list-item key={item}>{item}</s-list-item>)}</s-unordered-list>}
        {packetResult.packetZip?.base64 && <a download={packetResult.packetZip.name} href={`data:application/zip;base64,${packetResult.packetZip.base64}`}>Download SPL draft ZIP</a>}
        <s-paragraph>Submitted: no · Signed by app: no</s-paragraph>
      </s-section>}

      {!demo && <s-section heading="Plans">
        <s-paragraph>{subscriptions.length ? `Active plan: ${subscriptions[0].name}` : "Choose a plan to unlock packet preparation. Billing approval is handled by Shopify."}</s-paragraph>
        <Form method="post">
          <input type="hidden" name="intent" value="subscribe" />
          <s-select name="plan" label="Monthly plan" value={selectedPlan}>
            {Object.entries(PLANS).map(([key, plan]) => <s-option key={key} value={key}>{plan.label} · ${plan.price.toFixed(2)}/month · up to {plan.productLimit} products</s-option>)}
          </s-select>
          <s-button type="submit" variant="secondary" {...(busy ? { loading: true } : {})}>Review plan with Shopify</s-button>
        </Form>
      </s-section>}
      <s-section slot="aside" heading="What Glacier does not do">
        <s-paragraph>Glacier does not decide whether a product is exempt, guarantee compliance, sign FDA forms, or submit a filing. You review each source and make those decisions.</s-paragraph>
      </s-section>
    </s-page>
  );
}

export const headers: HeadersFunction = (args) => boundary.headers(args);
