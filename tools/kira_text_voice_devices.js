(() => {
  "use strict";

  const panel = document.querySelector("#devicePanel");
  if (!panel || panel.hidden) return;

  const cameraSelect = document.querySelector("#cameraDevice");
  const microphoneSelect = document.querySelector("#microphoneDevice");
  const speakerSelect = document.querySelector("#speakerDevice");
  const cameraPreview = document.querySelector("#cameraPreview");
  const stillPreview = document.querySelector("#stillPreview");
  const cameraIndicator = document.querySelector("#cameraIndicator");
  const microphoneIndicator = document.querySelector("#microphoneIndicator");
  const visualIndicator = document.querySelector("#visualIndicator");
  const deviceStatus = document.querySelector("#deviceStatus");
  const observationStatus = document.querySelector("#observationStatus");
  const asrStatus = document.querySelector("#asrStatus");
  const inputLevel = document.querySelector("#microphoneLevel");
  const transcript = document.querySelector("#pushToTalkTranscript");
  const cameraToggle = document.querySelector("#cameraToggle");
  const cameraOff = document.querySelector("#cameraOff");
  const lookNow = document.querySelector("#lookNow");
  const microphoneTest = document.querySelector("#microphoneTest");
  const continuousHearingToggle = document.querySelector("#continuousHearingToggle");
  const microphoneMute = document.querySelector("#microphoneMute");
  const speakerTest = document.querySelector("#speakerTest");
  const holdToTalk = document.querySelector("#holdToTalk");
  const useTranscript = document.querySelector("#useTranscript");
  const refreshDevices = document.querySelector("#refreshDevices");

  const asrEndpoint = String(panel.dataset.asrEndpoint || "http://127.0.0.1:8770").replace(/\/$/, "");
  const shellApiToken = String(panel.dataset.shellApiToken || "");
  const asrToken = String(panel.dataset.asrToken || "");
  const visualEndpoint = String(panel.dataset.visualEndpoint || "http://127.0.0.1:8771").replace(/\/$/, "");
  const visualToken = String(panel.dataset.visualToken || "");
  const sampleIntervalMs = Math.max(2000, Number(panel.dataset.sampleIntervalMs || 5000));

  function shellHeaders(extra = {}) {
    return { ...extra, "X-Kira-Shell-Token": shellApiToken };
  }

  let cameraStream = null;
  let cameraBinding = null;
  let visualFrameInFlight = false;
  let visualRequestController = null;
  let qwenLookInFlight = false;
  let qwenLookRequestController = null;
  let conversationPipelineBusy = false;
  let voicePipelineBusy = false;
  let microphoneStream = null;
  let microphoneContext = null;
  let microphoneFrame = 0;
  let continuousHearingStream = null;
  let continuousHearingContext = null;
  let continuousHearingFrame = 0;
  let continuousHearingRecorder = null;
  let continuousHearingChunks = [];
  let continuousSpeechStartedAt = 0;
  let continuousSilenceStartedAt = 0;
  let continuousBinding = null;
  let continuousTranscriptionInFlight = false;
  let asrRequestController = null;
  let voicePlaybackPollTimer = 0;
  let synthesizedVoicePlaying = false;
  let cameraSampleTimer = 0;
  let pushToTalkStream = null;
  let recorder = null;
  let recorderChunks = [];
  let discardRecorder = false;
  let recordingTimeout = 0;
  let temporaryObservation = null;
  let lastBindingKey = "";

  window.addEventListener("kira-chat-busy", event => {
    conversationPipelineBusy = event?.detail?.busy === true;
  });
  window.addEventListener("kira-voice-pipeline-busy", event => {
    voicePipelineBusy = event?.detail?.busy === true;
  });

  function setIndicator(element, enabled, label) {
    element.classList.toggle("on", !!enabled);
    element.classList.toggle("off", !enabled);
    element.textContent = `${label}: ${enabled ? "ON" : "OFF"}`;
  }

  function selectedPersonBinding() {
    const selected = String(candidateEl?.value || "");
    const active = String(state?.active_candidate || "");
    const activationRevision = String(state?.last_activation_at || "");
    return {
      selected,
      active,
      label: String(state?.active_label || selected || "none"),
      accepted: !!selected && selected === active,
      activationRevision,
      sensoryLease: String(state?.sensory_lease || ""),
      key: `${selected}|${active}|${activationRevision}`,
    };
  }

  function clearCanvas() {
    const context = stillPreview.getContext("2d");
    context.clearRect(0, 0, stillPreview.width, stillPreview.height);
  }

  function clearTemporaryVisualContext(reason) {
    temporaryObservation = null;
    clearCanvas();
    observationStatus.textContent = `${reason}. Temporary visual context cleared; no image was saved or carried to another person.`;
  }

  function clearPersonBoundTranscript(reason) {
    transcript.value = "";
    asrStatus.textContent = `${reason}. Temporary transcript cleared and was not sent.`;
  }

  function purgePersonBoundSensoryState(reason) {
    if (visualRequestController) visualRequestController.abort();
    if (qwenLookRequestController) qwenLookRequestController.abort();
    if (asrRequestController) asrRequestController.abort();
    visualRequestController = null;
    qwenLookRequestController = null;
    asrRequestController = null;
    stopPushToTalk(true);
    stopContinuousHearing(reason, true);
    stopMicrophoneLevel(reason);
    stopCamera(reason);
    clearPersonBoundTranscript(reason);
  }

  async function purgeRemoteSensoryState(binding, reason) {
    if (!binding?.accepted || !binding.sensoryLease) return false;
    try {
      const response = await fetch("/api/sensory/purge", {
        method: "POST",
        headers: shellHeaders({ "Content-Type": "application/json" }),
        cache: "no-store",
        body: JSON.stringify({ sensory_lease: binding.sensoryLease, reason }),
      });
      const result = await response.json();
      if (!response.ok || !result.ok) return false;
      if (String(state?.active_candidate || "") === binding.active) {
        state.sensory_lease = String(result.sensory_lease || "");
      }
      return true;
    } catch (_error) {
      return false;
    }
  }

  function selectedConstraint(select) {
    const value = String(select.value || "");
    return value ? { exact: value } : undefined;
  }

  function fillDeviceSelect(select, devices, fallbackLabel) {
    const previous = select.value;
    select.innerHTML = "";
    if (!devices.length) {
      const option = document.createElement("option");
      option.value = "";
      option.textContent = `No ${fallbackLabel.toLowerCase()} detected`;
      select.appendChild(option);
      return;
    }
    devices.forEach((device, index) => {
      const option = document.createElement("option");
      option.value = device.deviceId;
      option.textContent = device.label || `${fallbackLabel} ${index + 1}`;
      select.appendChild(option);
    });
    if ([...select.options].some(option => option.value === previous)) select.value = previous;
  }

  async function enumerateDevices() {
    if (!navigator.mediaDevices?.enumerateDevices) {
      deviceStatus.textContent = "This WebView does not expose media-device selection.";
      return;
    }
    try {
      const devices = await navigator.mediaDevices.enumerateDevices();
      fillDeviceSelect(cameraSelect, devices.filter(device => device.kind === "videoinput"), "Camera");
      fillDeviceSelect(microphoneSelect, devices.filter(device => device.kind === "audioinput"), "Microphone");
      fillDeviceSelect(speakerSelect, devices.filter(device => device.kind === "audiooutput"), "Speaker / output");
      deviceStatus.textContent = "Camera and microphone are independent. Device names may remain generic until Windows grants that device permission.";
    } catch (error) {
      deviceStatus.textContent = `Device enumeration failed: ${error.message}`;
    }
  }

  function canvasJpegBlob(canvas) {
    return new Promise((resolve, reject) => {
      canvas.toBlob(blob => {
        if (blob && blob.size) resolve(blob);
        else reject(new Error("the temporary JPEG encoder returned no frame"));
      }, "image/jpeg", 0.72);
    });
  }

  function visualCueValue(result, name) {
    const cue = Array.isArray(result?.cues)
      ? result.cues.find(item => item && item.name === name)
      : null;
    return cue ? cue.value : "unavailable";
  }

  async function checkVisualHealth({ quiet = false } = {}) {
    if (!visualToken) {
      if (!quiet) observationStatus.textContent = "Visual cues are unavailable: the isolated sidecar session token is missing. Local preview remains available.";
      return false;
    }
    try {
      const response = await fetch(`${visualEndpoint}/health`, {
        headers: { "X-Kira-Visual-Token": visualToken },
        cache: "no-store",
      });
      const result = await response.json();
      const ready = !!(response.ok && result.status === "ready" && result.capability?.available);
      setIndicator(visualIndicator, ready, "Visual cues");
      if (!quiet) {
        observationStatus.textContent = ready
          ? `Bounded local visual cues ready (${result.capability.backend}). They cannot identify Robert and do not create speech or memory.`
          : `Local visual-cue backend unavailable (${result.capability?.reason || result.status || "unknown"}). Camera preview can still be used without interpretation.`;
      }
      return ready;
    } catch (error) {
      setIndicator(visualIndicator, false, "Visual cues");
      if (!quiet) observationStatus.textContent = `Visual sidecar unavailable: ${error.message}. Camera preview can still be used without interpretation.`;
      return false;
    }
  }

  async function purgeVisualBaseline(binding) {
    if (!binding?.accepted || !binding.sensoryLease || !visualToken) return false;
    try {
      const response = await fetch(`${visualEndpoint}/api/purge`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Kira-Visual-Token": visualToken,
          "X-Kira-Person": binding.active,
          "X-Kira-Activation-Revision": binding.activationRevision,
          "X-Kira-Sensory-Lease": binding.sensoryLease,
        },
        body: "{}",
      });
      return response.ok;
    } catch (_error) {
      return false;
    }
  }

  async function deriveVisualCues(binding, blob, reason) {
    if (visualFrameInFlight || !visualToken) return false;
    visualFrameInFlight = true;
    const controller = new AbortController();
    visualRequestController = controller;
    try {
      const response = await fetch(`${visualEndpoint}/api/derive-cues`, {
        method: "POST",
        headers: {
          "Content-Type": "image/jpeg",
          "X-Kira-Visual-Token": visualToken,
          "X-Kira-Person": binding.active,
          "X-Kira-Activation-Revision": binding.activationRevision,
          "X-Kira-Sensory-Lease": binding.sensoryLease,
        },
        body: blob,
        signal: controller.signal,
      });
      const result = await response.json();
      const current = selectedPersonBinding();
      if (!current.accepted || current.key !== binding.key) return false;
      if (!response.ok || !result.ok) {
        observationStatus.textContent = `Temporary visual cue unavailable (${result.capability?.reason || result.error || "sidecar rejected frame"}). The frame was discarded.`;
        return false;
      }
      const cueConfidence = Math.max(
        0.1,
        ...result.cues.map(item => Math.max(0, Math.min(1, Number(item?.confidence || 0)))),
      );
      const cueResponse = await fetch("/api/sensory/cue", {
        method: "POST",
        headers: shellHeaders({ "Content-Type": "application/json" }),
        cache: "no-store",
        signal: controller.signal,
        body: JSON.stringify({
          sensory_lease: binding.sensoryLease,
          fact: {
            modality: "visual",
            event: "non_identifying_local_frame_cues",
            cues: result.cues,
          },
          source: {
            kind: "local_visual_perception_sidecar",
            backend: String(result.source || ""),
            person_session_bound: true,
          },
          observed_at: String(result.observed_at || new Date().toISOString()),
          confidence: cueConfidence,
          attributes: {
            capture_reason: reason,
            identity_inference_performed: false,
            automatic_spoken_response: false,
            automatic_memory_write: false,
          },
        }),
      });
      const accepted = await cueResponse.json();
      if (!cueResponse.ok || !accepted.ok) {
        observationStatus.textContent = "Local frame cues were derived but rejected by the active person's temporary sensory gate. The frame was discarded.";
        return false;
      }
      const brightness = visualCueValue(result, "brightness_class");
      const motion = visualCueValue(result, "motion_class");
      const faceCount = visualCueValue(result, "coarse_face_count");
      observationStatus.textContent = `Temporary local cues for ${binding.label}: light ${brightness}; movement ${motion}; face count ${faceCount}. No identity was inferred, and no speech or memory was created.`;
      return true;
    } catch (error) {
      if (error.name !== "AbortError") {
        observationStatus.textContent = `Temporary visual-cue processing failed: ${error.message}. Encoded frame bytes were discarded; preview pixels remain only until cleared or replaced.`;
      }
      return false;
    } finally {
      if (visualRequestController === controller) visualRequestController = null;
      visualFrameInFlight = false;
    }
  }

  async function jpegBlobToPlainBase64(blob) {
    const values = new Uint8Array(await blob.arrayBuffer());
    let encoded = "";
    try {
      const chunkSize = 0x8000;
      for (let offset = 0; offset < values.length; offset += chunkSize) {
        encoded += String.fromCharCode(...values.subarray(offset, offset + chunkSize));
      }
      return btoa(encoded);
    } finally {
      values.fill(0);
      encoded = "";
    }
  }

  async function deriveQwenOneStillCue(binding, blob, capturedAt) {
    if (qwenLookInFlight) {
      observationStatus.textContent = "A previous explicit Qwen one-still look is still finishing.";
      return false;
    }
    qwenLookInFlight = true;
    const controller = new AbortController();
    qwenLookRequestController = controller;
    let transientJpegBase64 = "";
    try {
      transientJpegBase64 = await jpegBlobToPlainBase64(blob);
      const response = await fetch("/api/sensory/qwen-look", {
        method: "POST",
        headers: shellHeaders({ "Content-Type": "application/json" }),
        cache: "no-store",
        signal: controller.signal,
        body: JSON.stringify({
          sensory_lease: binding.sensoryLease,
          person_id: binding.active,
          activation_revision: binding.activationRevision,
          captured_at: capturedAt,
          jpeg_base64: transientJpegBase64,
        }),
      });
      transientJpegBase64 = "";
      const accepted = await response.json();
      const current = selectedPersonBinding();
      if (!current.accepted || current.key !== binding.key) return false;
      if (!response.ok || !accepted.ok) {
        observationStatus.textContent = `Explicit Qwen one-still look was not used (${accepted.error || "failed closed"}). The still was discarded; no identity or memory was created.`;
        return false;
      }
      observationStatus.textContent = `One short-lived Qwen vision cue is ready for ${binding.label} until ${accepted.cue_expires_at_utc}. It used one still only; visible screen text was untrusted, no identity was evaluated, and no image or appearance memory was saved.`;
      return true;
    } catch (error) {
      if (error.name !== "AbortError") {
        observationStatus.textContent = `Explicit Qwen one-still look failed closed: ${error.message}. The still was discarded without identity or memory.`;
      }
      return false;
    } finally {
      transientJpegBase64 = "";
      if (qwenLookRequestController === controller) qwenLookRequestController = null;
      qwenLookInFlight = false;
    }
  }

  async function captureFrame(reason) {
    const binding = selectedPersonBinding();
    if (!cameraStream || cameraPreview.readyState < 2) {
      observationStatus.textContent = "Camera preview is off or not ready.";
      return false;
    }
    if (!binding.sensoryLease || binding.key !== cameraBinding?.key) {
      clearTemporaryVisualContext("Observation blocked because the camera is not bound to this exact activation");
      return false;
    }
    if (!binding.accepted) {
      clearTemporaryVisualContext("Observation blocked because the selected person is not the active person");
      return false;
    }
    if (reason === "low_rate_sample" && (conversationPipelineBusy || voicePipelineBusy || visualFrameInFlight || qwenLookInFlight)) {
      return false;
    }
    const width = Math.max(1, cameraPreview.videoWidth || 640);
    const height = Math.max(1, cameraPreview.videoHeight || 360);
    stillPreview.width = width;
    stillPreview.height = height;
    stillPreview.getContext("2d").drawImage(cameraPreview, 0, 0, width, height);
    const capturedAt = new Date().toISOString();
    temporaryObservation = {
      person: binding.active,
      capturedAt,
      reason,
      width,
      height,
    };
    observationStatus.textContent = `${reason === "look_now" ? "One still" : "Low-rate sample"} captured transiently for ${binding.label}; deriving bounded non-identifying local cues.`;
    try {
      const blob = await canvasJpegBlob(stillPreview);
      const boundedTasks = [deriveVisualCues(binding, blob, reason)];
      if (reason === "look_now") {
        boundedTasks.push(deriveQwenOneStillCue(binding, blob, capturedAt));
      }
      await Promise.all(boundedTasks);
    } catch (error) {
      observationStatus.textContent = `Temporary visual frame could not be reduced: ${error.message}. Nothing was saved.`;
    }
    return true;
  }

  function stopCamera(reason = "Camera turned off") {
    const previousBinding = cameraBinding;
    if (visualRequestController) visualRequestController.abort();
    if (qwenLookRequestController) qwenLookRequestController.abort();
    visualRequestController = null;
    qwenLookRequestController = null;
    if (cameraSampleTimer) window.clearInterval(cameraSampleTimer);
    cameraSampleTimer = 0;
    if (cameraStream) cameraStream.getTracks().forEach(track => track.stop());
    cameraStream = null;
    cameraBinding = null;
    cameraPreview.srcObject = null;
    cameraToggle.textContent = "Camera On";
    setIndicator(cameraIndicator, false, "Camera");
    clearTemporaryVisualContext(reason);
    void purgeVisualBaseline(previousBinding);
  }

  async function startCamera() {
    if (!navigator.mediaDevices?.getUserMedia) throw new Error("camera capture is unavailable in this WebView");
    const binding = selectedPersonBinding();
    if (!binding.accepted || !binding.sensoryLease) throw new Error("start the selected person's conversation before enabling their temporary visual pathway");
    const constraint = selectedConstraint(cameraSelect);
    cameraStream = await navigator.mediaDevices.getUserMedia({
      video: constraint ? { deviceId: constraint, width: { ideal: 640 }, height: { ideal: 360 } } : true,
      audio: false,
    });
    cameraPreview.srcObject = cameraStream;
    await cameraPreview.play();
    cameraBinding = binding;
    cameraToggle.textContent = "Camera Off";
    setIndicator(cameraIndicator, true, "Camera");
    const visualReady = await checkVisualHealth({ quiet: true });
    observationStatus.textContent = visualReady
      ? `Local preview is on for ${binding.label}. Low-rate frames become bounded non-identifying cues and are then discarded.`
      : "Local preview is on, but the visual-cue backend is unavailable. Frames remain local and are not interpreted or saved.";
    cameraSampleTimer = window.setInterval(() => void captureFrame("low_rate_sample"), sampleIntervalMs);
    await enumerateDevices();
  }

  function stopMicrophoneLevel(reason = "Microphone muted") {
    if (microphoneFrame) cancelAnimationFrame(microphoneFrame);
    microphoneFrame = 0;
    if (microphoneStream) microphoneStream.getTracks().forEach(track => track.stop());
    microphoneStream = null;
    if (microphoneContext) microphoneContext.close().catch(() => {});
    microphoneContext = null;
    inputLevel.value = 0;
    microphoneTest.textContent = "Test Microphone Level";
    setIndicator(microphoneIndicator, false, "Microphone");
    deviceStatus.textContent = `${reason}. No microphone audio was saved.`;
  }

  async function startMicrophoneLevel() {
    if (!navigator.mediaDevices?.getUserMedia) throw new Error("microphone capture is unavailable in this WebView");
    const constraint = selectedConstraint(microphoneSelect);
    microphoneStream = await navigator.mediaDevices.getUserMedia({
      video: false,
      audio: constraint ? { deviceId: constraint, echoCancellation: true, noiseSuppression: true } : true,
    });
    microphoneContext = new AudioContext();
    const source = microphoneContext.createMediaStreamSource(microphoneStream);
    const analyser = microphoneContext.createAnalyser();
    analyser.fftSize = 512;
    source.connect(analyser);
    const values = new Uint8Array(analyser.fftSize);
    const updateMeter = () => {
      analyser.getByteTimeDomainData(values);
      let total = 0;
      for (const value of values) {
        const normalized = (value - 128) / 128;
        total += normalized * normalized;
      }
      inputLevel.value = Math.min(1, Math.sqrt(total / values.length) * 4);
      microphoneFrame = requestAnimationFrame(updateMeter);
    };
    updateMeter();
    microphoneTest.textContent = "Stop Level Test";
    setIndicator(microphoneIndicator, true, "Microphone");
    deviceStatus.textContent = "Input-level test is live. This may be a different device from the selected camera; no audio is being saved.";
    await enumerateDevices();
  }

  function stopContinuousUtterance(discard = false) {
    if (!continuousHearingRecorder || continuousHearingRecorder.state === "inactive") return;
    continuousHearingRecorder._kiraDiscard = !!discard;
    continuousHearingRecorder.stop();
  }

  function startContinuousUtterance(binding) {
    if (!continuousHearingStream || continuousHearingRecorder || continuousTranscriptionInFlight || synthesizedVoicePlaying || window.kiraLocalMediaOutputActive) return;
    const utteranceRecorder = new MediaRecorder(continuousHearingStream, preferredRecorderOptions());
    continuousHearingRecorder = utteranceRecorder;
    continuousHearingChunks = [];
    continuousSpeechStartedAt = performance.now();
    continuousSilenceStartedAt = 0;
    utteranceRecorder._kiraDiscard = false;
    utteranceRecorder.ondataavailable = event => {
      if (event.data?.size) continuousHearingChunks.push(event.data);
    };
    utteranceRecorder.onstop = async () => {
      const chunks = continuousHearingChunks;
      continuousHearingChunks = [];
      const discard = !!utteranceRecorder._kiraDiscard;
      if (continuousHearingRecorder === utteranceRecorder) continuousHearingRecorder = null;
      continuousSpeechStartedAt = 0;
      continuousSilenceStartedAt = 0;
      if (discard || !chunks.length) return;
      const current = selectedPersonBinding();
      if (!current.accepted || current.key !== binding.key) return;
      continuousTranscriptionInFlight = true;
      try {
        const blob = new Blob(chunks, { type: utteranceRecorder.mimeType || "audio/webm" });
        await transcribeRecording(blob, binding, { continuous: true });
      } finally {
        continuousTranscriptionInFlight = false;
      }
    };
    utteranceRecorder.start(250);
    asrStatus.textContent = `Possible speech detected for ${binding.label}; collecting one bounded temporary utterance.`;
  }

  async function refreshSynthesizedVoiceGate() {
    try {
      const response = await fetch("/api/voice-playback", {
        headers: shellHeaders(),
        cache: "no-store",
      });
      const result = await response.json();
      synthesizedVoicePlaying = !!(response.ok && result.playing);
    } catch (_error) {
      synthesizedVoicePlaying = true;
    }
    if (synthesizedVoicePlaying) stopContinuousUtterance(true);
    window.kiraSetPersonVoicePlaybackState?.(synthesizedVoicePlaying);
  }

  function continuousHearingLoop(analyser, values) {
    if (!continuousHearingStream) return;
    analyser.getByteTimeDomainData(values);
    let total = 0;
    for (const value of values) {
      const normalized = (value - 128) / 128;
      total += normalized * normalized;
    }
    const rms = Math.sqrt(total / values.length);
    inputLevel.value = Math.min(1, rms * 4);
    const now = performance.now();
    const binding = selectedPersonBinding();
    if (!binding.accepted || binding.key !== continuousBinding?.key) {
      stopContinuousHearing("Active person changed", true);
      return;
    }
    const localOutputPlaying = !!window.kiraLocalMediaOutputActive;
    if (synthesizedVoicePlaying || localOutputPlaying) {
      if (continuousHearingRecorder) stopContinuousUtterance(true);
      continuousSilenceStartedAt = 0;
    } else if (rms >= 0.035) {
      continuousSilenceStartedAt = 0;
      startContinuousUtterance(binding);
    } else if (continuousHearingRecorder) {
      if (!continuousSilenceStartedAt) continuousSilenceStartedAt = now;
      const speechDuration = now - continuousSpeechStartedAt;
      if ((speechDuration >= 450 && now - continuousSilenceStartedAt >= 900) || speechDuration >= 15000) {
        stopContinuousUtterance(false);
      }
    }
    continuousHearingFrame = requestAnimationFrame(() => continuousHearingLoop(analyser, values));
  }

  function stopContinuousHearing(reason = "Continuous hearing stopped", discard = true) {
    if (continuousHearingFrame) cancelAnimationFrame(continuousHearingFrame);
    continuousHearingFrame = 0;
    if (voicePlaybackPollTimer) window.clearInterval(voicePlaybackPollTimer);
    voicePlaybackPollTimer = 0;
    stopContinuousUtterance(discard);
    if (continuousHearingStream) continuousHearingStream.getTracks().forEach(track => track.stop());
    continuousHearingStream = null;
    if (continuousHearingContext) continuousHearingContext.close().catch(() => {});
    continuousHearingContext = null;
    continuousBinding = null;
    synthesizedVoicePlaying = false;
    continuousHearingToggle.textContent = "Start continuous hearing";
    setIndicator(microphoneIndicator, !!microphoneStream, "Microphone");
    inputLevel.value = 0;
    if (reason) asrStatus.textContent = `${reason}. Raw room audio was not saved.`;
  }

  async function startContinuousHearing() {
    const binding = selectedPersonBinding();
    if (!binding.accepted || !binding.sensoryLease) {
      asrStatus.textContent = "Continuous hearing requires one exact active person and a current temporary sensory lease.";
      return;
    }
    if (!window.MediaRecorder || !navigator.mediaDevices?.getUserMedia) {
      asrStatus.textContent = "Continuous local hearing is unavailable in this WebView.";
      return;
    }
    if (!(await checkAsrHealth())) return;
    stopPushToTalk(true);
    if (microphoneStream) stopMicrophoneLevel("Switching from level test to continuous hearing");
    const constraint = selectedConstraint(microphoneSelect);
    continuousHearingStream = await navigator.mediaDevices.getUserMedia({
      video: false,
      audio: constraint
        ? { deviceId: constraint, echoCancellation: true, noiseSuppression: true, autoGainControl: true }
        : { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
    });
    continuousHearingContext = new AudioContext();
    const source = continuousHearingContext.createMediaStreamSource(continuousHearingStream);
    const analyser = continuousHearingContext.createAnalyser();
    analyser.fftSize = 512;
    source.connect(analyser);
    continuousBinding = binding;
    continuousHearingToggle.textContent = "Stop continuous hearing";
    setIndicator(microphoneIndicator, true, "Microphone");
    asrStatus.textContent = `Temporary local hearing capture is active for ${binding.label}. The current attention/initiative foundation does not yet treat every transcript as heard; no cue forces speech, action, or memory.`;
    await refreshSynthesizedVoiceGate();
    voicePlaybackPollTimer = window.setInterval(refreshSynthesizedVoiceGate, 350);
    continuousHearingLoop(analyser, new Uint8Array(analyser.fftSize));
  }

  async function checkAsrHealth() {
    if (!asrToken) {
      asrStatus.textContent = "ASR blocked: the isolated sidecar session token is unavailable.";
      return false;
    }
    try {
      const response = await fetch(`${asrEndpoint}/health`, {
        headers: { "X-Kira-ASR-Token": asrToken },
        cache: "no-store",
      });
      const result = await response.json();
      if (!response.ok || result.status !== "ready") throw new Error(result.error || result.status || "not ready");
      asrStatus.textContent = `ASR ready: ${result.model_id}; cache-only CPU sidecar; raw audio persistence off.`;
      return true;
    } catch (error) {
      asrStatus.textContent = `ASR sidecar unavailable: ${error.message}. Typed chat remains available.`;
      return false;
    }
  }

  function preferredRecorderOptions() {
    const types = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus"];
    const mimeType = types.find(type => window.MediaRecorder?.isTypeSupported?.(type));
    return mimeType ? { mimeType, audioBitsPerSecond: 96000 } : { audioBitsPerSecond: 96000 };
  }

  async function transcribeRecording(blob, binding, options = {}) {
    const continuous = !!options.continuous;
    let controller = null;
    asrStatus.textContent = continuous
      ? "Interpreting one temporary local utterance; it will not become a command or permanent transcript."
      : "Transcribing locally; the message will remain editable and will not send automatically...";
    try {
      if (asrRequestController) asrRequestController.abort();
      controller = new AbortController();
      asrRequestController = controller;
      const response = await fetch(`${asrEndpoint}/api/transcribe`, {
        method: "POST",
        headers: {
          "Content-Type": blob.type || "application/octet-stream",
          "X-Kira-ASR-Token": asrToken,
          "X-Kira-Person": binding.active,
          "X-Kira-Activation-Revision": binding.activationRevision,
          "X-Kira-Sensory-Lease": binding.sensoryLease,
        },
        body: blob,
        signal: controller.signal,
      });
      const result = await response.json();
      if (!response.ok || !result.ok) throw new Error(result.message || result.error || "transcription failed");
      const current = selectedPersonBinding();
      if (!current.accepted || current.key !== binding.key) {
        clearPersonBoundTranscript("Transcription finished after the active person changed");
        return;
      }
      let perceptionAccepted = false;
      if (result.text && binding.sensoryLease) {
        try {
          const cueResponse = await fetch("/api/sensory/cue", {
            method: "POST",
            headers: shellHeaders({ "Content-Type": "application/json" }),
            cache: "no-store",
            body: JSON.stringify({
              sensory_lease: binding.sensoryLease,
              fact: {
                modality: "auditory",
                event: "possible_speech",
                speaker: "robert_or_unknown",
                transcript: String(result.text || ""),
              },
              source: {
                kind: "local_microphone_asr",
                model_id: String(result.model_id || ""),
                person_session_bound: true,
              },
              observed_at: new Date().toISOString(),
              confidence: Math.max(0, Math.min(1, Number(result.language_probability || 0.5))),
              attributes: {
                language: String(result.language || ""),
                segment_count: Array.isArray(result.segments) ? result.segments.length : 0,
                automatic_spoken_response: false,
                automatic_memory_write: false,
              },
            }),
          });
          const cueResult = await cueResponse.json();
          perceptionAccepted = !!(cueResponse.ok && cueResult.ok);
        } catch (_error) {
          perceptionAccepted = false;
        }
      }
      if (!continuous) transcript.value = String(result.text || "");
      asrStatus.textContent = result.text
        ? (perceptionAccepted
          ? (continuous
            ? "Temporary speech cue entered the active person's bounded sensory gate and is eligible for a separate private attention decision; no automatic reply or memory was created."
            : "A temporary person-bound speech cue was accepted for possible private attention. It was not automatically treated as heard, spoken about, remembered, or sent as a chat message. The transcript remains editable below.")
          : (continuous
            ? "Temporary speech was transcribed but rejected by the person-bound sensory gate."
            : "Transcript ready, but the temporary sensory cue was not accepted. Edit it below; nothing was sent automatically."))
        : "No speech was recognized. The raw recording was discarded.";
    } catch (error) {
      if (error.name !== "AbortError") {
        asrStatus.textContent = `ASR failed: ${error.message}. The raw recording was discarded; typed chat still works.`;
      }
    } finally {
      if (asrRequestController === controller) asrRequestController = null;
    }
  }

  async function startPushToTalk(event) {
    if (event?.button !== undefined && event.button !== 0) return;
    event?.preventDefault();
    if (recorder) return;
    if (continuousHearingStream) {
      asrStatus.textContent = "Stop continuous hearing before using Hold to Talk.";
      return;
    }
    const binding = selectedPersonBinding();
    if (!binding.accepted) {
      asrStatus.textContent = "Push-to-talk blocked: start the selected person's text + voice conversation first.";
      return;
    }
    if (!(await checkAsrHealth())) return;
    try {
      const constraint = selectedConstraint(microphoneSelect);
      pushToTalkStream = await navigator.mediaDevices.getUserMedia({
        video: false,
        audio: constraint ? { deviceId: constraint, echoCancellation: true, noiseSuppression: true } : true,
      });
      recorderChunks = [];
      discardRecorder = false;
      recorder = new MediaRecorder(pushToTalkStream, preferredRecorderOptions());
      recorder.ondataavailable = chunkEvent => {
        if (chunkEvent.data?.size) recorderChunks.push(chunkEvent.data);
      };
      recorder.onstop = async () => {
        const finishedRecorder = recorder;
        recorder = null;
        window.clearTimeout(recordingTimeout);
        recordingTimeout = 0;
        if (pushToTalkStream) pushToTalkStream.getTracks().forEach(track => track.stop());
        pushToTalkStream = null;
        holdToTalk.classList.remove("recording");
        holdToTalk.textContent = "Hold to Talk";
        setIndicator(microphoneIndicator, !!microphoneStream, "Microphone");
        const chunks = recorderChunks;
        recorderChunks = [];
        if (discardRecorder) {
          asrStatus.textContent = "Push-to-talk cancelled and raw audio discarded.";
          return;
        }
        const blob = new Blob(chunks, { type: finishedRecorder.mimeType || "audio/webm" });
        await transcribeRecording(blob, binding);
      };
      recorder.start(250);
      holdToTalk.classList.add("recording");
      holdToTalk.textContent = "Release to Transcribe";
      setIndicator(microphoneIndicator, true, "Microphone");
      asrStatus.textContent = `Recording only while held for ${binding.label}; maximum 30 seconds; raw audio will not be saved.`;
      recordingTimeout = window.setTimeout(() => stopPushToTalk(false), 30000);
    } catch (error) {
      if (pushToTalkStream) pushToTalkStream.getTracks().forEach(track => track.stop());
      pushToTalkStream = null;
      recorder = null;
      asrStatus.textContent = `Push-to-talk could not start: ${error.message}`;
    }
  }

  function stopPushToTalk(discard = false) {
    if (!recorder || recorder.state === "inactive") return;
    discardRecorder = !!discard;
    recorder.stop();
  }

  window.kiraNotifyLocalOutputStarted = source => {
    stopContinuousUtterance(true);
    stopPushToTalk(true);
    const label = String(source || "local output").replace(/[_-]+/g, " ");
    asrStatus.textContent = `${label} started; any overlapping raw microphone fragment was discarded to prevent speaker-loop transcription.`;
  };

  async function testSpeakerOutput() {
    try {
      stopContinuousUtterance(true);
      window.kiraSetLocalOutputSource?.("speaker_test", true);
      const context = new AudioContext();
      const oscillator = context.createOscillator();
      const gain = context.createGain();
      const destination = context.createMediaStreamDestination();
      gain.gain.value = 0.035;
      oscillator.frequency.value = 523.25;
      oscillator.connect(gain).connect(destination);
      const audio = new Audio();
      audio.srcObject = destination.stream;
      if (speakerSelect.value && typeof audio.setSinkId === "function") await audio.setSinkId(speakerSelect.value);
      await audio.play();
      oscillator.start();
      window.setTimeout(async () => {
        oscillator.stop();
        audio.pause();
        destination.stream.getTracks().forEach(track => track.stop());
        await context.close();
        window.kiraSetLocalOutputSource?.("speaker_test", false);
      }, 300);
      deviceStatus.textContent = typeof audio.setSinkId === "function"
        ? "Short test tone routed to the selected browser output."
        : "Short test tone played; this WebView cannot route to a selected output device.";
    } catch (error) {
      window.kiraSetLocalOutputSource?.("speaker_test", false);
      deviceStatus.textContent = `Speaker test failed: ${error.message}`;
    }
  }

  cameraToggle.onclick = async () => {
    if (cameraStream) {
      stopCamera();
      return;
    }
    try {
      await startCamera();
    } catch (error) {
      stopCamera(`Camera start failed: ${error.message}`);
    }
  };
  cameraOff.onclick = () => {
    const binding = selectedPersonBinding();
    stopCamera("Immediate camera-off control used");
    purgeRemoteSensoryState(binding, "immediate_camera_off");
  };
  lookNow.onclick = () => void captureFrame("look_now");
  microphoneTest.onclick = async () => {
    if (continuousHearingStream) stopContinuousHearing("Continuous hearing stopped for microphone level test", true);
    if (microphoneStream) {
      stopMicrophoneLevel("Microphone level test stopped");
      return;
    }
    try {
      await startMicrophoneLevel();
    } catch (error) {
      stopMicrophoneLevel(`Microphone test failed: ${error.message}`);
    }
  };
  microphoneMute.onclick = () => {
    const binding = selectedPersonBinding();
    stopPushToTalk(true);
    stopContinuousHearing("Immediate mute control used", true);
    stopMicrophoneLevel("Immediate mute control used");
    clearPersonBoundTranscript("Immediate mute control used");
    purgeRemoteSensoryState(binding, "immediate_microphone_off");
  };
  continuousHearingToggle.onclick = async () => {
    if (continuousHearingStream) {
      stopContinuousHearing("Continuous hearing stopped", true);
      return;
    }
    try {
      await startContinuousHearing();
    } catch (error) {
      stopContinuousHearing(`Continuous hearing failed: ${error.message}`, true);
    }
  };
  speakerTest.onclick = testSpeakerOutput;
  refreshDevices.onclick = enumerateDevices;
  useTranscript.onclick = () => {
    const reviewed = transcript.value.trim();
    if (!reviewed) {
      asrStatus.textContent = "There is no reviewed transcript to move.";
      return;
    }
    document.querySelector("#chatText").value = reviewed;
    document.querySelector("#chatText").focus();
    asrStatus.textContent = "Reviewed transcript moved to the message box. Press Send manually when ready.";
  };
  holdToTalk.addEventListener("pointerdown", startPushToTalk);
  holdToTalk.addEventListener("pointerup", () => stopPushToTalk(false));
  holdToTalk.addEventListener("pointercancel", () => stopPushToTalk(true));
  holdToTalk.addEventListener("keydown", event => {
    if ((event.code === "Space" || event.code === "Enter") && !event.repeat) startPushToTalk(event);
  });
  holdToTalk.addEventListener("keyup", event => {
    if (event.code === "Space" || event.code === "Enter") stopPushToTalk(false);
  });
  cameraSelect.addEventListener("change", () => {
    if (cameraStream) stopCamera("Camera selection changed");
  });
  microphoneSelect.addEventListener("change", () => {
    stopPushToTalk(true);
    if (continuousHearingStream) stopContinuousHearing("Microphone selection changed", true);
    if (microphoneStream) stopMicrophoneLevel("Microphone selection changed");
  });
  candidateEl.addEventListener("change", () => purgePersonBoundSensoryState("Selected person changed"));
  navigator.mediaDevices?.addEventListener?.("devicechange", enumerateDevices);
  window.addEventListener("pagehide", () => {
    purgePersonBoundSensoryState("Window closing");
  });

  window.setInterval(() => {
    const binding = selectedPersonBinding();
    const key = binding.key;
    if (lastBindingKey && key !== lastBindingKey) purgePersonBoundSensoryState("Active or selected person changed");
    lastBindingKey = key;
  }, 500);

  setIndicator(cameraIndicator, false, "Camera");
  setIndicator(microphoneIndicator, false, "Microphone");
  setIndicator(visualIndicator, false, "Visual cues");
  clearTemporaryVisualContext("Startup default");
  enumerateDevices();
  checkAsrHealth();
  checkVisualHealth({ quiet: true });
})();
