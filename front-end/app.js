const API_URL = "https://a56pf9f1q4.execute-api.us-east-1.amazonaws.com/prod";
const API_KEY = "QxOZxqI9vT4kdIizrQrM71E9bOf8LgZaOpTXINng";

// Generated SDK client (used for search)
const apigClient = apigClientFactory.newClient({ apiKey: API_KEY });

// ---------- Search ----------
document.getElementById("search-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const q = document.getElementById("search-input").value.trim();
  const status = document.getElementById("search-status");
  const results = document.getElementById("results");

  results.innerHTML = "";
  status.textContent = "Searching…";

  try {
    const res = await apigClient.searchGet({ q: q }, {}, {});
    const photos = (res.data && res.data.results) || [];

    if (photos.length === 0) {
      status.textContent = `No photos found for "${q}".`;
      return;
    }

    status.textContent = `${photos.length} photo(s) found for "${q}"`;
    photos.forEach((p) => {
      const card = document.createElement("div");
      card.className = "photo";

      const img = document.createElement("img");
      img.src = p.url;
      img.alt = (p.labels || []).join(", ");
      img.loading = "lazy";

      const labels = document.createElement("div");
      labels.className = "labels";
      (p.labels || []).forEach((l) => {
        const tag = document.createElement("span");
        tag.textContent = l;
        labels.appendChild(tag);
      });

      card.append(img, labels);
      results.appendChild(card);
    });
  } catch (err) {
    console.error("Search error:", err);
    status.textContent = "Search failed. Check the browser console for details.";
  }
});

// ---------- Upload ----------
// Uses PUT /photos/{object} on the same API. Plain fetch is used here because the
// generated SDK serializes request bodies, which corrupts binary image data.
document.getElementById("upload-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const file = document.getElementById("file-input").files[0];
  const status = document.getElementById("upload-status");
  if (!file) return;

  // "Sam ,Sally,," -> "Sam, Sally"
  const customLabels = document.getElementById("labels-input").value
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean)
    .join(", ");

  // Unique, URL-safe object key
  const key = `${Date.now()}-${file.name.replace(/\s+/g, "-")}`;

  const headers = {
    "x-api-key": API_KEY,
    "Content-Type": file.type || "image/jpeg",
  };
  if (customLabels) headers["x-amz-meta-customLabels"] = customLabels;

  status.textContent = "Uploading…";
  try {
    const res = await fetch(`${API_URL}/photos/${encodeURIComponent(key)}`, {
      method: "PUT",
      headers: headers,
      body: file,
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    status.textContent = `Uploaded "${file.name}"${customLabels ? ` with labels: ${customLabels}` : ""}. It will be searchable in about 10 seconds.`;
    e.target.reset();
  } catch (err) {
    console.error("Upload error:", err);
    status.textContent = "Upload failed. Check the browser console for details.";
  }
});
