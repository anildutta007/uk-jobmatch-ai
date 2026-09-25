// UK JobMatch AI - Frontend Application Controller

document.addEventListener("DOMContentLoaded", () => {
  // Initialize Lucide Icons
  if (window.lucide) {
    window.lucide.createIcons();
  }

  // State
  let currentFile = null;
  let sampleCvText = null;
  let sampleCvFilename = null;
  let currentExtractedCvText = "";
  let currentLoadedJobs = [];
  let selectedJobIds = new Set();
  let tailorResultData = null;
  let activeJobIndex = 0;
  let activeDocType = "cv";

  // DOM Elements
  const dropZone = document.getElementById("dropZone");
  const fileInput = document.getElementById("fileInput");
  const dropEmptyState = document.getElementById("dropEmptyState");
  const fileSelectedState = document.getElementById("fileSelectedState");
  const fileNameDisplay = document.getElementById("fileNameDisplay");
  const fileSizeDisplay = document.getElementById("fileSizeDisplay");
  const removeFileBtn = document.getElementById("removeFileBtn");
  const loadSampleBtn = document.getElementById("loadSampleBtn");

  // Tailoring DOM Elements
  const selectionBar = document.getElementById("selectionBar");
  const selectedCountDisplay = document.getElementById("selectedCountDisplay");
  const tailorAppBtn = document.getElementById("tailorAppBtn");
  const clearSelectionBtn = document.getElementById("clearSelectionBtn");
  const tailorLoadingModal = document.getElementById("tailorLoadingModal");
  const tailorModal = document.getElementById("tailorModal");
  const closeTailorModalBtn = document.getElementById("closeTailorModalBtn");
  const dismissTailorModalBtn = document.getElementById("dismissTailorModalBtn");
  const tailorAiBadge = document.getElementById("tailorAiBadge");
  const tailorSubtitle = document.getElementById("tailorSubtitle");
  const jobTabsNav = document.getElementById("jobTabsNav");
  const activeJobTitleCompany = document.getElementById("activeJobTitleCompany");
  const activeJobSkillsList = document.getElementById("activeJobSkillsList");
  const amendmentsSection = document.getElementById("amendmentsSection");
  const amendmentsList = document.getElementById("amendmentsList");
  const docTypeCvBtn = document.getElementById("docTypeCvBtn");
  const docTypeCoverBtn = document.getElementById("docTypeCoverBtn");
  const activeDocumentLabel = document.getElementById("activeDocumentLabel");
  const downloadPdfBtn = document.getElementById("downloadPdfBtn");
  const downloadPdfBtnText = document.getElementById("downloadPdfBtnText");
  const copyActiveDocBtn = document.getElementById("copyActiveDocBtn");
  const copyBtnText = document.getElementById("copyBtnText");
  const copyIcon = document.getElementById("copyIcon");
  const downloadActiveDocBtn = document.getElementById("downloadActiveDocBtn");
  const tailorDocumentText = document.getElementById("tailorDocumentText");

  const locationSelect = document.getElementById("locationSelect");
  const scoreThreshold = document.getElementById("scoreThreshold");
  const scoreThresholdValue = document.getElementById("scoreThresholdValue");
  const findJobsBtn = document.getElementById("findJobsBtn");
  const btnLabel = document.getElementById("btnLabel");

  const progressSection = document.getElementById("progressSection");
  const progressHeading = document.getElementById("progressHeading");
  const progressDetail = document.getElementById("progressDetail");
  const profileSection = document.getElementById("profileSection");
  const resultsSection = document.getElementById("resultsSection");
  const jobsList = document.getElementById("jobsList");
  const resultCountBadge = document.getElementById("resultCountBadge");

  // Profile DOM Elements
  const profileName = document.getElementById("profileName");
  const profileTitle = document.getElementById("profileTitle");
  const profileAiBadge = document.getElementById("profileAiBadge");
  const profileSkills = document.getElementById("profileSkills");
  const profileKeywords = document.getElementById("profileKeywords");
  const profileSummary = document.getElementById("profileSummary");

  // Settings Modal Elements
  const openSettingsBtn = document.getElementById("openSettingsBtn");
  const closeSettingsBtn = document.getElementById("closeSettingsBtn");
  const cancelSettingsBtn = document.getElementById("cancelSettingsBtn");
  const settingsModal = document.getElementById("settingsModal");
  const saveKeyBtn = document.getElementById("saveKeyBtn");
  const modalKeyInput = document.getElementById("modalKeyInput");
  const modalKeyStatus = document.getElementById("modalKeyStatus");
  const keyStatusBadge = document.getElementById("keyStatusBadge");
  const keyIndicator = document.getElementById("keyIndicator");
  const keyStatusText = document.getElementById("keyStatusText");

  // 1. Initial Configuration Check
  async function checkConfig() {
    try {
      const resp = await fetch("/api/config");
      if (resp.ok) {
        const config = await resp.json();
        updateKeyStatusUI(config.has_gemini_key);
      }
    } catch (err) {
      console.warn("Failed to fetch initial config", err);
    }
  }

  function updateKeyStatusUI(hasKey) {
    if (hasKey) {
      keyIndicator.className = "w-2 h-2 rounded-full bg-emerald-400";
      keyStatusText.textContent = "Gemini Agent Ready";
      keyStatusBadge.className = "flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20";
      modalKeyStatus.textContent = "Configured in Environment";
      modalKeyStatus.className = "font-bold text-emerald-400";
    } else {
      keyIndicator.className = "w-2 h-2 rounded-full bg-amber-400 animate-pulse";
      keyStatusText.textContent = "No Key (Heuristic Mode)";
      keyStatusBadge.className = "flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20 cursor-pointer";
      modalKeyStatus.textContent = "Not set (Click to add)";
      modalKeyStatus.className = "font-bold text-amber-400";
    }
  }

  checkConfig();

  // 2. Settings Modal Events
  openSettingsBtn.addEventListener("click", () => settingsModal.classList.remove("hidden"));
  keyStatusBadge.addEventListener("click", () => settingsModal.classList.remove("hidden"));
  closeSettingsBtn.addEventListener("click", () => settingsModal.classList.add("hidden"));
  cancelSettingsBtn.addEventListener("click", () => settingsModal.classList.add("hidden"));

  saveKeyBtn.addEventListener("click", async () => {
    const key = modalKeyInput.value.trim();
    if (!key) {
      alert("Please enter a valid Gemini API key.");
      return;
    }
    saveKeyBtn.disabled = true;
    saveKeyBtn.textContent = "Saving...";

    try {
      const resp = await fetch("/api/save-key", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_key: key })
      });
      const data = await resp.json();
      if (resp.ok) {
        updateKeyStatusUI(true);
        settingsModal.classList.add("hidden");
        modalKeyInput.value = "";
      } else {
        alert(data.detail || "Error saving API key.");
      }
    } catch (err) {
      alert("Network error saving key: " + err.message);
    } finally {
      saveKeyBtn.disabled = false;
      saveKeyBtn.textContent = "Save Key";
    }
  });

  // 3. Slider Threshold Sync
  scoreThreshold.addEventListener("input", (e) => {
    scoreThresholdValue.textContent = `${parseFloat(e.target.value).toFixed(1)} / 10`;
  });

  // 4. File Drag and Drop Handlers
  dropZone.addEventListener("click", (e) => {
    if (e.target !== removeFileBtn && !removeFileBtn.contains(e.target)) {
      fileInput.click();
    }
  });

  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("border-indigo-500", "bg-slate-900/80");
  });

  dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("border-indigo-500", "bg-slate-900/80");
  });

  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("border-indigo-500", "bg-slate-900/80");
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileSelected(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener("change", (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileSelected(e.target.files[0]);
    }
  });

  function handleFileSelected(file) {
    currentFile = file;
    sampleCvText = null;
    fileNameDisplay.textContent = file.name;
    fileSizeDisplay.textContent = `${(file.size / 1024).toFixed(1)} KB`;
    dropEmptyState.classList.add("hidden");
    fileSelectedState.classList.remove("hidden");
    if (window.lucide) window.lucide.createIcons();
  }

  removeFileBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    currentFile = null;
    sampleCvText = null;
    currentExtractedCvText = "";
    selectedJobIds.clear();
    updateSelectionBarUI();
    fileInput.value = "";
    dropEmptyState.classList.remove("hidden");
    fileSelectedState.classList.add("hidden");
  });

  // 5. Load Sample CV Handler
  loadSampleBtn.addEventListener("click", async () => {
    try {
      loadSampleBtn.classList.add("opacity-50");
      const resp = await fetch("/api/sample-cv");
      if (resp.ok) {
        const data = await resp.json();
        sampleCvText = data.content;
        sampleCvFilename = data.filename;
        currentExtractedCvText = data.content;
        currentFile = null;
        fileInput.value = "";

        fileNameDisplay.textContent = data.filename;
        fileSizeDisplay.textContent = "Pre-loaded Sample CV (Senior Full-Stack)";
        dropEmptyState.classList.add("hidden");
        fileSelectedState.classList.remove("hidden");
        if (window.lucide) window.lucide.createIcons();
      }
    } catch (err) {
      alert("Failed to load sample CV: " + err.message);
    } finally {
      loadSampleBtn.classList.remove("opacity-50");
    }
  });

  // 6. Step Animation Controller
  function setStep(stepNum, heading, detail) {
    progressHeading.textContent = heading;
    progressDetail.textContent = detail;

    for (let i = 1; i <= 4; i++) {
      const el = document.getElementById(`step${i}`);
      el.classList.remove("active", "done");
      if (i < stepNum) {
        el.classList.add("done");
      } else if (i === stepNum) {
        el.classList.add("active");
      }
    }
  }

  // 7. Find & Score Jobs Submission
  findJobsBtn.addEventListener("click", async () => {
    if (!currentFile && !sampleCvText) {
      alert("Please upload your CV or click 'Load Sample CV' to proceed.");
      return;
    }

    // UI State: Loading
    findJobsBtn.disabled = true;
    btnLabel.textContent = "Evaluating...";
    progressSection.classList.remove("hidden");
    profileSection.classList.add("hidden");
    resultsSection.classList.add("hidden");
    jobsList.innerHTML = "";

    // Step 1: Parsing
    setStep(1, "Parsing CV Document...", "Extracting clean text structure from your resume file.");

    const formData = new FormData();
    if (currentFile) {
      formData.append("file", currentFile);
    } else if (sampleCvText) {
      formData.append("cv_text", sampleCvText);
    }

    formData.append("target_location", locationSelect.value);
    formData.append("min_score", scoreThreshold.value);

    // Timed step visual animations while waiting for server response
    const stepTimer1 = setTimeout(() => {
      setStep(2, "Gemini Agent Analyzing Profile...", "Detecting core technologies, seniority, and matching keywords.");
    }, 1200);

    const stepTimer2 = setTimeout(() => {
      setStep(3, "Scanning UK Job Boards...", "Aggregating active UK tech positions across Adzuna, Arbeitnow, and Remotive.");
    }, 3200);

    const stepTimer3 = setTimeout(() => {
      setStep(4, "Deep Scoring Out of 10...", "Gemini LLM Agent evaluating role alignment, skill gaps, and interview advice.");
    }, 5500);

    try {
      const resp = await fetch("/api/match-jobs", {
        method: "POST",
        body: formData
      });

      clearTimeout(stepTimer1);
      clearTimeout(stepTimer2);
      clearTimeout(stepTimer3);

      const data = await resp.json();

      if (!resp.ok) {
        throw new Error(data.detail || "Server error while processing jobs.");
      }

      currentExtractedCvText = data.cv_text || sampleCvText || "";
      currentLoadedJobs = data.jobs || [];
      selectedJobIds.clear();
      updateSelectionBarUI();

      // Mark all steps done
      for (let i = 1; i <= 4; i++) {
        document.getElementById(`step${i}`).className = "step-card done bg-slate-950/60 border border-emerald-500/40 rounded-xl p-3 text-center space-y-1";
      }

      // Display Extracted Profile
      renderProfile(data.profile);

      // Display Results
      renderJobs(data.jobs, data.ai_powered);

      // Scroll smoothly to results
      setTimeout(() => {
        profileSection.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 300);

    } catch (err) {
      alert("Error: " + err.message);
      progressSection.classList.add("hidden");
    } finally {
      findJobsBtn.disabled = false;
      btnLabel.textContent = "Find & Score Matching Jobs";
    }
  });

  // 8. Render Extracted Profile
  function renderProfile(profile) {
    if (!profile) return;
    profileName.textContent = profile.candidate_name || "Candidate";
    profileTitle.textContent = `${profile.target_title || "Software Professional"} • ${profile.years_experience || "5+ years"}`;

    if (profile.ai_powered) {
      profileAiBadge.textContent = "Gemini LLM Extracted";
      profileAiBadge.className = "text-[10px] px-2 py-0.5 rounded-full font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30";
    } else {
      profileAiBadge.textContent = "Heuristic Extracted (Add API key for full LLM)";
      profileAiBadge.className = "text-[10px] px-2 py-0.5 rounded-full font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/30";
    }

    // Skills
    profileSkills.innerHTML = "";
    (profile.core_technical_skills || []).forEach(skill => {
      const span = document.createElement("span");
      span.className = "px-2.5 py-1 text-xs font-semibold rounded-lg bg-indigo-500/10 text-indigo-300 border border-indigo-500/25";
      span.textContent = skill;
      profileSkills.appendChild(span);
    });

    // Keywords
    profileKeywords.innerHTML = "";
    (profile.search_keywords || []).forEach(kw => {
      const span = document.createElement("span");
      span.className = "px-2 py-0.5 text-[11px] rounded bg-slate-800 text-slate-300 border border-slate-700";
      span.textContent = kw;
      profileKeywords.appendChild(span);
    });

    profileSummary.textContent = `"${profile.summary || 'Strong technical foundation with relevant industry competencies.'}"`;
    profileSection.classList.remove("hidden");
    if (window.lucide) window.lucide.createIcons();
  }

  // 9. Render Scored Job Cards
  function renderJobs(jobs, isAiPowered) {
    jobsList.innerHTML = "";
    resultsSection.classList.remove("hidden");
    resultCountBadge.textContent = `${jobs.length} Jobs Match`;

    if (!jobs || jobs.length === 0) {
      jobsList.innerHTML = `
        <div class="bg-slate-900/60 border border-slate-800 rounded-2xl p-12 text-center space-y-3">
          <i data-lucide="search-x" class="w-10 h-10 mx-auto text-slate-500"></i>
          <h4 class="text-base font-bold text-white">No jobs met the minimum score threshold</h4>
          <p class="text-xs text-slate-400">Try lowering the minimum score slider or widening the UK location filter.</p>
        </div>
      `;
      if (window.lucide) window.lucide.createIcons();
      return;
    }

    jobs.forEach((job, index) => {
      const score = Number(job.match_score).toFixed(1);
      const jobId = job.id || `${job.title}_${job.company}_${index}`;
      const isSelected = selectedJobIds.has(jobId);
      
      // Score Color Classes
      let scoreBadgeClass = "bg-emerald-500/15 text-emerald-400 border-emerald-500/30";
      let scoreGlow = "shadow-emerald-500/10";
      if (score >= 8.5) {
        scoreBadgeClass = "bg-emerald-500/15 text-emerald-400 border-emerald-500/30";
        scoreGlow = "shadow-emerald-500/20";
      } else if (score >= 7.0) {
        scoreBadgeClass = "bg-indigo-500/15 text-indigo-400 border-indigo-500/30";
        scoreGlow = "shadow-indigo-500/20";
      } else if (score >= 5.5) {
        scoreBadgeClass = "bg-amber-500/15 text-amber-400 border-amber-500/30";
        scoreGlow = "shadow-amber-500/20";
      } else {
        scoreBadgeClass = "bg-slate-700/40 text-slate-300 border-slate-600";
        scoreGlow = "shadow-none";
      }

      const card = document.createElement("div");
      card.className = isSelected 
        ? "bg-slate-900/90 border-2 border-indigo-500/80 ring-4 ring-indigo-500/15 rounded-2xl p-6 transition-all shadow-xl shadow-indigo-950/40 space-y-4"
        : "bg-slate-900/80 hover:bg-slate-900 border border-slate-800 hover:border-slate-700 rounded-2xl p-6 transition-all shadow-lg hover:shadow-xl space-y-4 animate-fade-in";

      // Matched skills pills
      const matchedPills = (job.matching_skills || []).map(skill => 
        `<span class="inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-300 border border-emerald-500/20">
          <i data-lucide="check" class="w-3 h-3 text-emerald-400"></i> ${skill}
        </span>`
      ).join(" ");

      // Missing skills pills
      const missingPills = (job.missing_skills || []).map(skill => 
        `<span class="inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-md bg-rose-500/10 text-rose-300 border border-rose-500/20">
          <i data-lucide="alert-circle" class="w-3 h-3 text-rose-400"></i> ${skill}
        </span>`
      ).join(" ");

      card.innerHTML = `
        <!-- Card Top Bar: Selection Toggle & Score Badge -->
        <div class="flex items-center justify-between gap-3 border-b border-slate-800/80 pb-3">
          <label class="inline-flex items-center gap-2 cursor-pointer select-none px-3 py-1.5 rounded-xl border transition text-xs font-semibold ${isSelected ? 'bg-indigo-600/20 border-indigo-500 text-indigo-300 ring-2 ring-indigo-500/20' : 'bg-slate-800/80 hover:bg-slate-700/80 border-slate-700 text-slate-300'}">
            <input type="checkbox" class="job-select-checkbox w-4 h-4 rounded text-indigo-600 focus:ring-indigo-500 bg-slate-900 border-slate-600 cursor-pointer" data-job-id="${jobId}" ${isSelected ? 'checked' : ''}>
            <span>${isSelected ? '✓ Selected for Tailoring' : 'Select to Tailor (Max 3)'}</span>
          </label>
          <div class="flex items-center gap-2 text-xs text-slate-400">
            <span class="text-[11px] font-semibold uppercase tracking-wider text-slate-400">${job.match_tier || "Match"}</span>
            <div class="px-2.5 py-1 rounded-lg font-extrabold text-sm border flex items-center gap-1 shadow-sm ${scoreBadgeClass} ${scoreGlow}">
              <i data-lucide="award" class="w-3.5 h-3.5"></i>
              <span>${score}</span>
              <span class="text-[10px] font-semibold opacity-75">/ 10</span>
            </div>
          </div>
        </div>

        <div class="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
          <!-- Job Details -->
          <div class="space-y-1.5 flex-1">
            <div class="flex flex-wrap items-center gap-2">
              <a href="${job.url}" target="_blank" rel="noopener noreferrer" class="text-lg font-bold text-white hover:text-indigo-400 hover:underline flex items-center gap-1.5 group transition" title="Click to open actual job listing">
                <span>${job.title}</span>
                <i data-lucide="external-link" class="w-4 h-4 text-slate-500 group-hover:text-indigo-400 transition"></i>
              </a>
              <span class="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">${job.source || "UK Board"}</span>
            </div>
            
            <div class="flex flex-wrap items-center gap-3 text-xs text-slate-400">
              <span class="flex items-center gap-1 font-semibold text-slate-200">
                <i data-lucide="building" class="w-3.5 h-3.5 text-indigo-400"></i>
                ${job.company}
              </span>
              <span class="flex items-center gap-1">
                <i data-lucide="map-pin" class="w-3.5 h-3.5 text-slate-500"></i>
                ${job.location}
              </span>
              <span class="flex items-center gap-1 text-emerald-400 font-medium">
                <i data-lucide="banknote" class="w-3.5 h-3.5"></i>
                ${job.salary}
              </span>
            </div>
          </div>
        </div>

        <!-- Gemini Rationale Box -->
        <div class="bg-slate-950/60 rounded-xl p-3.5 border border-slate-800/80 space-y-1.5">
          <div class="flex items-center gap-1.5 text-xs font-bold text-indigo-300">
            <i data-lucide="sparkles" class="w-3.5 h-3.5 text-indigo-400"></i>
            <span>Gemini Match Evaluation</span>
          </div>
          <p class="text-xs text-slate-300 leading-relaxed">${job.rationale}</p>
        </div>

        <!-- Skills Breakdown Grid -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
          <div class="space-y-1">
            <span class="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Matched Competencies:</span>
            <div class="flex flex-wrap gap-1.5">
              ${matchedPills || '<span class="text-xs text-slate-500">General transferable skills</span>'}
            </div>
          </div>

          <div class="space-y-1">
            <span class="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Areas to Highlight / Gaps:</span>
            <div class="flex flex-wrap gap-1.5">
              ${missingPills || '<span class="text-xs text-emerald-400">No major gaps detected</span>'}
            </div>
          </div>
        </div>

        <!-- Application Tip -->
        ${job.application_tip ? `
          <div class="flex items-start gap-2 bg-indigo-950/20 border border-indigo-500/15 rounded-lg px-3 py-2 text-[11px] text-indigo-200">
            <i data-lucide="lightbulb" class="w-3.5 h-3.5 text-indigo-400 flex-shrink-0 mt-0.5"></i>
            <span><strong>Application Strategy:</strong> ${job.application_tip}</span>
          </div>
        ` : ''}

        <!-- Direct Job Listing Action -->
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-t border-slate-800/80 pt-3">
          <div class="flex items-center gap-2 text-xs text-slate-400">
            <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 text-[11px] font-medium">
              <i data-lucide="check-circle" class="w-3.5 h-3.5 text-emerald-400"></i> Direct Job Post (${job.source || "UK Board"})
            </span>
            <span class="text-slate-500">•</span>
            <span>${job.posted_date || "Active UK vacancy"}</span>
          </div>

          <a href="${job.url}" target="_blank" rel="noopener noreferrer" class="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-500 shadow-lg shadow-indigo-600/30 transition transform active:scale-[0.98]">
            <span>Open Specific Job Listing & Apply</span>
            <i data-lucide="external-link" class="w-4 h-4"></i>
          </a>
        </div>
      `;

      // Checkbox event
      const chk = card.querySelector(".job-select-checkbox");
      if (chk) {
        chk.addEventListener("change", (e) => {
          e.stopPropagation();
          if (chk.checked) {
            if (selectedJobIds.size >= 3) {
              alert("You can select up to 3 jobs at a time to tailor your CV and cover letters.");
              chk.checked = false;
              return;
            }
            selectedJobIds.add(jobId);
          } else {
            selectedJobIds.delete(jobId);
          }
          updateSelectionBarUI();
          renderJobs(currentLoadedJobs, true);
        });
      }

      jobsList.appendChild(card);
    });

    if (window.lucide) {
      window.lucide.createIcons();
    }
  }

  // 10. Selection Bar Controller
  function updateSelectionBarUI() {
    const count = selectedJobIds.size;
    selectedCountDisplay.textContent = count;
    if (count > 0) {
      selectionBar.classList.remove("hidden");
    } else {
      selectionBar.classList.add("hidden");
    }
  }

  clearSelectionBtn.addEventListener("click", () => {
    selectedJobIds.clear();
    updateSelectionBarUI();
    renderJobs(currentLoadedJobs, true);
  });

  // 11. Tailor Application Suite Handlers
  tailorAppBtn.addEventListener("click", async () => {
    if (selectedJobIds.size === 0) {
      alert("Please select at least 1 job (up to 3) from the list to tailor your application.");
      return;
    }
    if (!currentExtractedCvText) {
      alert("No CV content found. Please upload a CV or load the sample CV first.");
      return;
    }

    const selectedList = currentLoadedJobs.filter((j, idx) => {
      const jId = j.id || `${j.title}_${j.company}_${idx}`;
      return selectedJobIds.has(jId);
    });

    tailorLoadingModal.classList.remove("hidden");

    try {
      const resp = await fetch("/api/tailor-application", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          cv_text: currentExtractedCvText,
          selected_jobs: selectedList
        })
      });

      const data = await resp.json();
      if (!resp.ok || !data.success) {
        throw new Error(data.detail || data.error || "Failed to tailor application.");
      }

      tailorLoadingModal.classList.add("hidden");
      renderTailorModal(data);
    } catch (err) {
      tailorLoadingModal.classList.add("hidden");
      alert("Application Tailoring Error: " + err.message);
    }
  });

  function getApplicationsList() {
    if (!tailorResultData) return [];
    if (Array.isArray(tailorResultData.applications) && tailorResultData.applications.length > 0) {
      return tailorResultData.applications;
    }
    // Fallback if legacy structure returned
    return [{
      job_title: "Target Position",
      company: "Target Employer",
      target_skills_highlighted: [],
      key_amendments: tailorResultData.key_amendments || [],
      tailored_cv: tailorResultData.tailored_cv || "",
      cover_letter: (tailorResultData.cover_letters && tailorResultData.cover_letters[0]) ? tailorResultData.cover_letters[0].content : ""
    }];
  }

  function renderTailorModal(data) {
    tailorResultData = data;
    activeJobIndex = 0;
    activeDocType = "cv";

    // AI Badge
    if (data.ai_powered) {
      const model = data.model_used ? `Gemini (${data.model_used})` : "Gemini 2.0 Flash";
      tailorAiBadge.textContent = `${model} Tailored`;
      tailorAiBadge.className = "text-[10px] px-2 py-0.5 rounded-full font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20";
    } else {
      tailorAiBadge.textContent = "Spec-Aligned Heuristic Tailored";
      tailorAiBadge.className = "text-[10px] px-2 py-0.5 rounded-full font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20";
    }

    const applications = getApplicationsList();
    if (applications.length === 0) {
      alert("No application packages were generated.");
      return;
    }

    renderJobTabs();
    selectJob(0);
    tailorModal.classList.remove("hidden");
    if (window.lucide) window.lucide.createIcons();
  }

  function renderJobTabs() {
    jobTabsNav.innerHTML = "";
    const applications = getApplicationsList();

    applications.forEach((app, idx) => {
      const btn = document.createElement("button");
      btn.type = "button";
      const isSelected = (idx === activeJobIndex);
      btn.className = `flex items-center gap-2 px-3.5 py-1.5 rounded-xl text-xs font-semibold transition cursor-pointer shrink-0 ${
        isSelected
          ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30 border border-indigo-500"
          : "bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-700 hover:text-white"
      }`;

      const company = app.company || `Company ${idx + 1}`;
      const title = app.job_title || "Target Role";
      btn.innerHTML = `
        <span class="w-5 h-5 rounded-full ${isSelected ? 'bg-white/20 text-white' : 'bg-slate-800 text-slate-400'} flex items-center justify-center text-[10px] font-bold">${idx + 1}</span>
        <div class="text-left leading-tight">
          <span class="block font-bold">${company}</span>
          <span class="block text-[10px] ${isSelected ? 'text-indigo-200' : 'text-slate-400'} truncate max-w-[150px]">${title}</span>
        </div>
      `;
      btn.addEventListener("click", () => selectJob(idx));
      jobTabsNav.appendChild(btn);
    });
  }

  function selectJob(index) {
    activeJobIndex = index;
    renderJobTabs();

    const applications = getApplicationsList();
    const app = applications[activeJobIndex] || applications[0];

    // Update Active Job Title & Company
    activeJobTitleCompany.textContent = `${app.job_title || "Target Role"} @ ${app.company || "Target Employer"}`;

    // Update Skills Elevated Badge Row
    activeJobSkillsList.innerHTML = "";
    const skills = app.target_skills_highlighted || [];
    if (skills.length > 0) {
      const label = document.createElement("span");
      label.className = "text-[11px] text-slate-400 mr-1";
      label.textContent = "Spec Skills Elevated:";
      activeJobSkillsList.appendChild(label);

      skills.slice(0, 6).forEach(skill => {
        const span = document.createElement("span");
        span.className = "inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-300 border border-emerald-500/25";
        span.innerHTML = `<i data-lucide="check" class="w-2.5 h-2.5"></i>${skill}`;
        activeJobSkillsList.appendChild(span);
      });
    }

    // Update Key Amendments
    const amendments = app.key_amendments || [];
    if (amendments.length > 0) {
      amendmentsSection.classList.remove("hidden");
      amendmentsList.innerHTML = amendments.map(item => `<li>${item}</li>`).join("");
    } else {
      amendmentsSection.classList.add("hidden");
    }

    updateDocTypeUI();
    if (window.lucide) window.lucide.createIcons();
  }

  function setDocType(docType) {
    activeDocType = docType;
    updateDocTypeUI();
    if (window.lucide) window.lucide.createIcons();
  }

  function updateDocTypeUI() {
    const applications = getApplicationsList();
    const app = applications[activeJobIndex] || applications[0];

    if (activeDocType === "cv") {
      docTypeCvBtn.className = "flex items-center gap-1.5 px-4 py-2 rounded-t-xl text-xs font-bold transition border-b-2 border-indigo-500 text-white bg-slate-900 cursor-pointer";
      docTypeCvBtn.querySelector("svg")?.classList.add("text-indigo-400");
      docTypeCoverBtn.className = "flex items-center gap-1.5 px-4 py-2 rounded-t-xl text-xs font-medium text-slate-400 hover:text-slate-200 transition border-b-2 border-transparent hover:border-slate-700 cursor-pointer";
      docTypeCoverBtn.querySelector("svg")?.classList.remove("text-indigo-400");

      activeDocumentLabel.textContent = `Submission-Ready CV (Optimized for ${app.job_title})`;
      tailorDocumentText.textContent = app.tailored_cv || "No tailored CV generated.";
      downloadPdfBtnText.textContent = "Download Formatted CV (PDF)";
    } else {
      docTypeCoverBtn.className = "flex items-center gap-1.5 px-4 py-2 rounded-t-xl text-xs font-bold transition border-b-2 border-indigo-500 text-white bg-slate-900 cursor-pointer";
      docTypeCoverBtn.querySelector("svg")?.classList.add("text-indigo-400");
      docTypeCvBtn.className = "flex items-center gap-1.5 px-4 py-2 rounded-t-xl text-xs font-medium text-slate-400 hover:text-slate-200 transition border-b-2 border-transparent hover:border-slate-700 cursor-pointer";
      docTypeCvBtn.querySelector("svg")?.classList.remove("text-indigo-400");

      activeDocumentLabel.textContent = `Spec-Focused Cover Letter for ${app.company} (${app.job_title})`;
      tailorDocumentText.textContent = app.cover_letter || "No cover letter generated.";
      downloadPdfBtnText.textContent = "Download Formatted Cover Letter (PDF)";
    }
  }

  docTypeCvBtn.addEventListener("click", () => setDocType("cv"));
  docTypeCoverBtn.addEventListener("click", () => setDocType("cover_letter"));

  // Download Executive PDF via Backend ReportLab Service
  downloadPdfBtn.addEventListener("click", async () => {
    const applications = getApplicationsList();
    const app = applications[activeJobIndex] || applications[0];
    const text = tailorDocumentText.textContent;
    if (!text) {
      alert("No content available to export as PDF.");
      return;
    }

    const originalText = downloadPdfBtnText.textContent;
    downloadPdfBtn.disabled = true;
    downloadPdfBtnText.textContent = "Generating PDF...";

    try {
      const candidateName = profileName?.textContent || "Candidate";
      const resp = await fetch("/api/download-cv-pdf", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          doc_type: activeDocType,
          content_text: text,
          candidate_name: candidateName,
          target_role: app.job_title || "Target Role",
          target_company: app.company || "Target Company",
          key_skills: app.target_skills_highlighted || []
        })
      });

      if (!resp.ok) {
        const errJson = await resp.json().catch(() => ({}));
        throw new Error(errJson.detail || "Failed to generate PDF document.");
      }

      const blob = await resp.blob();
      const safeCompany = (app.company || "Company").replace(/[^a-zA-Z0-9]/g, "_");
      const safeRole = (app.job_title || "Role").replace(/[^a-zA-Z0-9]/g, "_");
      const filename = activeDocType === "cv"
        ? `CV_${safeRole}.pdf`
        : `Cover_Letter_${safeCompany}_${safeRole}.pdf`;

      const downloadUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = downloadUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(downloadUrl);
    } catch (err) {
      alert("PDF Export Error: " + err.message);
    } finally {
      downloadPdfBtn.disabled = false;
      downloadPdfBtnText.textContent = originalText;
    }
  });

  // Copy to clipboard
  copyActiveDocBtn.addEventListener("click", async () => {
    const text = tailorDocumentText.textContent;
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      copyBtnText.textContent = "Copied!";
      copyIcon.setAttribute("data-lucide", "check");
      if (window.lucide) window.lucide.createIcons();
      setTimeout(() => {
        copyBtnText.textContent = "Copy";
        copyIcon.setAttribute("data-lucide", "copy");
        if (window.lucide) window.lucide.createIcons();
      }, 2000);
    } catch (e) {
      alert("Copied text to clipboard!");
    }
  });

  // Download document (.txt)
  downloadActiveDocBtn.addEventListener("click", () => {
    const applications = getApplicationsList();
    const app = applications[activeJobIndex] || applications[0];
    const text = tailorDocumentText.textContent;
    if (!text) return;

    const safeCompany = (app.company || "Company").replace(/[^a-zA-Z0-9]/g, "_");
    const safeRole = (app.job_title || "Role").replace(/[^a-zA-Z0-9]/g, "_");
    const filename = activeDocType === "cv"
      ? `CV_${safeRole}.txt`
      : `Cover_Letter_${safeCompany}_${safeRole}.txt`;

    const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  });

  closeTailorModalBtn.addEventListener("click", () => tailorModal.classList.add("hidden"));
  dismissTailorModalBtn.addEventListener("click", () => tailorModal.classList.add("hidden"));

});
