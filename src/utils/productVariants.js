// ──────────────────────────────────────────────────────────────
// Variant resolution: applies a selected option-set to a base product,
// recomputing displayed name, specs, and per-store prices.
// ──────────────────────────────────────────────────────────────

export function getDefaultVariantSelection(product) {
  if (!product?.variants) return {};
  const selection = {};
  for (const group of product.variants) {
    const def =
      group.options.find((o) => o.isDefault) || group.options[0];
    if (def) selection[group.label] = def.shortValue;
  }
  return selection;
}

function findOption(group, shortValue) {
  return group.options.find((o) => o.shortValue === shortValue) || null;
}

export function resolveProductVariant(product, selection) {
  if (!product?.variants?.length) {
    return {
      displayName: product?.name || '',
      specs: product?.specs || [],
      stores: product?.stores || [],
      images: product?.images || [],
      totalDelta: 0,
    };
  }

  let totalDelta = 0;
  let displayName = product.nameTemplate || product.name || '';
  const specOverrides = {};
  // Iterate in variant order; the LAST option whose `images` array is non-empty
  // wins. Convention: place the visual driver (e.g. Color) after non-visual
  // groups (Storage, RAM) so colour selection drives the gallery.
  let variantImages = null;

  for (const group of product.variants) {
    const chosenShort = selection?.[group.label];
    const chosen = chosenShort
      ? findOption(group, chosenShort)
      : group.options.find((o) => o.isDefault) || group.options[0];
    if (!chosen) continue;

    totalDelta += chosen.priceDelta || 0;
    if (product.nameTemplate) {
      displayName = displayName.replaceAll(`{${group.label}}`, chosen.shortValue);
    }
    if (group.specLabel) {
      specOverrides[group.specLabel] = chosen.value;
    }
    if (Array.isArray(chosen.images) && chosen.images.length > 0) {
      variantImages = chosen.images;
    }
  }

  if (!product.nameTemplate) displayName = product.name;

  const specs = (product.specs || []).map((s) =>
    specOverrides[s.label] ? { ...s, value: specOverrides[s.label] } : s,
  );

  const stores = (product.stores || []).map((s) => ({
    ...s,
    price: Math.max(0, (s.price || 0) + totalDelta),
  }));

  const images = variantImages || product.images || [];

  return { displayName, specs, stores, images, totalDelta };
}
