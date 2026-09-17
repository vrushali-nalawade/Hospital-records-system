import os

frontend_path = os.path.abspath(r"..\Hospital-records-system\src\lib\services\records-service.ts")
with open(frontend_path, "r", encoding="utf-8") as f:
    content = f.read()

target = """      // Poll document status until it is ready or failed
      onStatus("processing");
      let status: ProcessingStatus = "processing";
      let pollCount = 0;
      
      while (pollCount < 30) {
        await new Promise((res) => setTimeout(res, 1000));
        pollCount++;
        
        const statusRes = await fetch(`${API_URL}/documents/${docId}/status`, {
          headers: {
            "Authorization": headers["Authorization"]
          }
        });
        
        if (statusRes.ok) {
          const statusData = await statusRes.json();
          const apiStatus = statusData.status.toUpperCase();
          
          if (apiStatus === "READY" || apiStatus === "PROCESSED") {
            status = "ready";
            onStatus("ocr_completed");
            await new Promise((res) => setTimeout(res, 500));
            onStatus("extracted");
            await new Promise((res) => setTimeout(res, 500));
            onStatus("ready");
            break;
          } else if (apiStatus === "FAILED") {
            status = "failed";
            onStatus("failed");
            throw new Error("Document ingestion failed");
          }
        }
      }"""

replacement = """      // Poll document status until it is ready or failed
      onStatus("processing");
      let status: ProcessingStatus = "processing";
      let pollCount = 0;
      const maxPolls = 120; // 120s timeout to allow real EasyOCR + BGE-M3 model on CPU
      let docReady = false;
      let showedOcr = false;
      
      while (pollCount < maxPolls) {
        await new Promise((res) => setTimeout(res, 1000));
        pollCount++;
        
        try {
          const statusRes = await fetch(`${API_URL}/documents/${docId}/status`, {
            headers: {
              "Authorization": headers["Authorization"]
            }
          });
          
          if (statusRes.ok) {
            const statusData = await statusRes.json();
            const apiStatus = (statusData.status || "").toUpperCase();
            const jobStatus = (statusData.job_status || "").toUpperCase();
            
            if (apiStatus === "INDEXING" || jobStatus === "INDEXING") {
              if (!showedOcr) {
                onStatus("ocr_completed");
                showedOcr = true;
              }
            } else if (apiStatus === "READY" || apiStatus === "PROCESSED" || jobStatus === "COMPLETED") {
              status = "ready";
              docReady = true;
              onStatus("ocr_completed");
              await new Promise((res) => setTimeout(res, 400));
              onStatus("extracted");
              await new Promise((res) => setTimeout(res, 400));
              onStatus("ready");
              break;
            } else if (apiStatus === "FAILED" || jobStatus === "FAILED") {
              status = "failed";
              onStatus("failed");
              throw new Error(statusData.error_message || "Document ingestion failed");
            }
          }
        } catch (pollErr: any) {
          if (pollErr?.message && (pollErr.message.includes("failed") || pollErr.message.includes("Failed"))) {
            throw pollErr;
          }
        }
      }
      
      if (!docReady && status !== "ready") {
        const finalStatusRes = await fetch(`${API_URL}/documents/${docId}/status`, {
          headers: { "Authorization": headers["Authorization"] }
        }).catch(() => null);
        if (finalStatusRes?.ok) {
          const finalData = await finalStatusRes.json();
          const finalStatus = (finalData.status || "").toUpperCase();
          if (finalStatus === "READY" || finalStatus === "PROCESSED") {
            status = "ready";
            onStatus("ocr_completed");
            await new Promise((res) => setTimeout(res, 300));
            onStatus("extracted");
            await new Promise((res) => setTimeout(res, 300));
            onStatus("ready");
          } else {
            throw new Error("Document processing timeout. Document is still processing in the background.");
          }
        } else {
          throw new Error("Document processing status check failed.");
        }
      }"""

# Normalize CRLF / LF
content_norm = content.replace("\r\n", "\n")
target_norm = target.replace("\r\n", "\n")
replacement_norm = replacement.replace("\r\n", "\n")

if target_norm in content_norm:
    new_content = content_norm.replace(target_norm, replacement_norm, 1)
    with open(frontend_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print("SUCCESSFULLY REPLACED FRONTEND POLLING LOGIC")
else:
    print("TARGET NOT FOUND IN FRONTEND FILE")
