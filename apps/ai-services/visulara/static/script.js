document.addEventListener('DOMContentLoaded', () => {
    // --- DOM Elements ---
    
    // Steps
    const stepCategory = document.getElementById('step-category');
    const stepPersonalization = document.getElementById('step-personalization');
    const stepLoading = document.getElementById('step-loading');
    const stepPlayer = document.getElementById('step-player');
    
    // Inputs
    const categorySelect = document.getElementById('category-select');
    const selectedCategoryLabel = document.getElementById('selected-category-label');
    const nameInput = document.getElementById('name');
    const currentMoodInput = document.getElementById('current-mood');
    const meditationGoalInput = document.getElementById('meditation-goal');
    const avoidInput = document.getElementById('avoid');
    const audioAnchorSelect = document.getElementById('audio-anchor');
    const landscapeEnvSelect = document.getElementById('landscape-env');
    const voiceSelect = document.getElementById('voice-select');
    const durationSelect = document.getElementById('duration-select');
    const experienceSelect = document.getElementById('experience-select');
    const bodyFocusContainer = document.getElementById('body-focus-container');
    
    // Buttons
    const btnGenerate = document.getElementById('btn-generate');
    const btnRestart = document.getElementById('btn-restart');
    const btnDownloadMeditation = document.getElementById('btn-download-meditation');
    
    // Player Elements
    const bgMusic = document.getElementById('bg-music');
    const bgVolume = document.getElementById('bg-volume');
    const generatedTitle = document.getElementById('generated-title');
    const generatedSummary = document.getElementById('generated-summary');
    
    const audioMeditation = document.getElementById('audio-meditation');
    const audioSuggestion = document.getElementById('audio-suggestion');
    const audioAffirmation = document.getElementById('audio-affirmation');
    
    const track1UI = document.getElementById('track-1');
    const track2UI = document.getElementById('track-2');
    const track3UI = document.getElementById('track-3');
    
    const btnPlayPause = document.getElementById('btn-play-pause');
    const loopSuggestionBtn = document.getElementById('loop-suggestion');
    const loopAffirmationBtn = document.getElementById('loop-affirmation');
    
    // --- State ---
    let currentTrackIndex = 0; // 0 = meditation, 1 = suggestion, 2 = affirmation
    const tracks = [audioMeditation, audioSuggestion, audioAffirmation];
    const trackUIs = [track1UI, track2UI, track3UI];
    let isPlaying = false;
    let isSuggestionLoop = false;
    let isAffirmationLoop = false;
    let currentDownloadUrl = '';

    function showStep(stepToShow) {
        [stepCategory, stepPersonalization, stepLoading, stepPlayer].forEach((step) => {
            step.classList.add('hidden');
            step.classList.remove('active');
        });
        stepToShow.classList.remove('hidden');
        stepToShow.classList.add('active');
    }

    function syncCategoryLabel() {
        const selectedOption = categorySelect.options[categorySelect.selectedIndex];
        selectedCategoryLabel.textContent = selectedOption && selectedOption.value ? selectedOption.text : 'Relaxation';
    }

    // Background audio mapping based on anchor (using royalty free placeholders for now)
    const anchorToAudio = {
        "Gentle summer rain": "https://cdn.pixabay.com/download/audio/2021/08/04/audio_0625c1539c.mp3?filename=heavy-rain-nature-sounds-8186.mp3",
        "Soft wind rustling": "https://cdn.pixabay.com/download/audio/2021/08/09/audio_8846175084.mp3?filename=wind-in-trees-114613.mp3",
        "Crackling fireplace": "https://cdn.pixabay.com/download/audio/2022/02/07/audio_67e9140c83.mp3?filename=ambient-piano-amp-strings-10711.mp3", // fallback
        "Rhythmic ocean waves": "https://cdn.pixabay.com/download/audio/2021/08/09/audio_688a29a43a.mp3?filename=ocean-waves-112906.mp3",
        "Complete silence": ""
    };
    
    // --- Step 1: Form Collection ---
    
    // Body Focus Chips Interaction
    const chips = bodyFocusContainer.querySelectorAll('.chip');
    chips.forEach(chip => {
        const checkbox = chip.querySelector('input[type="checkbox"]');
        chip.addEventListener('click', (e) => {
            if(e.target !== checkbox) {
                checkbox.checked = !checkbox.checked;
            }
            if(checkbox.checked) {
                chip.style.backgroundColor = 'rgba(197, 163, 101, 0.2)';
                chip.style.borderColor = 'var(--primary)';
                chip.style.color = 'var(--primary)';
            } else {
                chip.style.backgroundColor = '';
                chip.style.borderColor = '';
                chip.style.color = '';
            }
        });
    });

    categorySelect.addEventListener('change', syncCategoryLabel);

    document.getElementById('btn-category-next').addEventListener('click', () => {
        if (!categorySelect.value) {
            alert('Please choose a meditation category first.');
            return;
        }
        syncCategoryLabel();
        showStep(stepPersonalization);
    });

    document.getElementById('btn-category-back').addEventListener('click', () => {
        showStep(stepCategory);
    });

    function getSelectedBodyFocus() {
        const selected = [];
        bodyFocusContainer.querySelectorAll('input[type="checkbox"]:checked').forEach(cb => {
            selected.push(cb.value);
        });
        return selected;
    }

    // Generate Button Click
    btnGenerate.addEventListener('click', async () => {
        if (!categorySelect.value || !durationSelect.value || !experienceSelect.value || !voiceSelect.value) {
            alert('Please complete the category, duration, experience level, and voice fields.');
            return;
        }

        const bodyTension = getSelectedBodyFocus();
        const payload = {
            name: nameInput.value.trim() || null,
            user_name: nameInput.value.trim() || null,
            category: categorySelect.value,
            emotion: currentMoodInput.value.trim() || null,
            goal: meditationGoalInput.value.trim() || null,
            avoid: avoidInput.value.trim() || null,
            stress_input: avoidInput.value.trim() || null,
            body_tension: bodyTension,
            body_tension_areas: bodyTension,
            body_focus: bodyTension.join(', ') || null,
            duration: Number(durationSelect.value),
            duration_minutes: Number(durationSelect.value),
            experience: experienceSelect.value,
            nature_sound: audioAnchorSelect.value,
            landscape: landscapeEnvSelect.value,
            user_name: nameInput.value.trim() || null,
            current_mood: currentMoodInput.value.trim() || null,
            meditation_goal: meditationGoalInput.value.trim() || null,
            audio_anchor: audioAnchorSelect.value,
            landscape_env: landscapeEnvSelect.value,
            voice: voiceSelect.value,
            voice_id: voiceSelect.value,
            experience_level: experienceSelect.value,
            persona: "Supportive Friend",
            language: "German" // Fixed to German per requirement
        };

        // Transition to Loading
        showStep(stepLoading);

        try {
            const response = await fetch('/api/v1/generate-meditation', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                throw new Error(`API returned status: ${response.status}`);
            }

            const data = await response.json();
            setupPlayer(data, payload.audio_anchor);
            
            // Transition to Player
            stepLoading.classList.remove('active');
            stepLoading.classList.add('hidden');
            stepPlayer.classList.remove('hidden');
            stepPlayer.classList.add('active');

        } catch (error) {
            console.error(error);
            alert("Oops! Something went wrong while generating your meditation. Please try again.");
            showStep(stepPersonalization);
        }
    });

    // --- Player Logic ---

    function setupPlayer(data, anchor) {
        const meditationTitle = data.meditation?.title || data.title || 'Meditation';
        const meditationSummary = data.meditation?.summary || data.summary || 'Your generated meditation is ready.';

        generatedTitle.textContent = meditationTitle;
        generatedSummary.textContent = meditationSummary;

        // Load AI Voices
        const sections = data.sections;
        
        if(sections.meditation) {
            audioMeditation.src = "data:audio/mpeg;base64," + sections.meditation.audio_base64;
        }
        if(sections.suggestion) {
            audioSuggestion.src = "data:audio/mpeg;base64," + sections.suggestion.audio_base64;
        }
        if(sections.affirmation) {
            audioAffirmation.src = "data:audio/mpeg;base64," + sections.affirmation.audio_base64;
        }

        if (currentDownloadUrl) {
            URL.revokeObjectURL(currentDownloadUrl);
            currentDownloadUrl = '';
        }

        if (sections.meditation && sections.meditation.audio_base64) {
            const audioBytes = atob(sections.meditation.audio_base64);
            const audioBuffer = new Uint8Array(audioBytes.length);
            for (let index = 0; index < audioBytes.length; index += 1) {
                audioBuffer[index] = audioBytes.charCodeAt(index);
            }
            const audioBlob = new Blob([audioBuffer], { type: 'audio/mpeg' });
            currentDownloadUrl = URL.createObjectURL(audioBlob);
            btnDownloadMeditation.disabled = false;
        } else {
            btnDownloadMeditation.disabled = true;
        }

        // Load Background Audio
        if(anchorToAudio[anchor]) {
            bgMusic.src = anchorToAudio[anchor];
            bgMusic.volume = bgVolume.value;
        } else {
            bgMusic.src = "";
        }

        // Reset state
        currentTrackIndex = 0;
        isPlaying = false;
        isSuggestionLoop = false;
        isAffirmationLoop = false;
        updateTrackUI();
        updatePlayBtnUI();
        loopSuggestionBtn.classList.remove('active');
        loopAffirmationBtn.classList.remove('active');
    }

    btnDownloadMeditation.addEventListener('click', () => {
        if (!currentDownloadUrl) return;

        const link = document.createElement('a');
        link.href = currentDownloadUrl;
        link.download = `${(generatedTitle.textContent || 'meditation').toLowerCase().replace(/[^a-z0-9]+/g, '-')}.mp3`;
        document.body.appendChild(link);
        link.click();
        link.remove();
    });

    btnPlayPause.addEventListener('click', () => {
        if (isPlaying) {
            pauseMeditation();
        } else {
            playMeditation();
        }
    });

    function playMeditation() {
        if (!tracks[currentTrackIndex].src) return;
        
        tracks[currentTrackIndex].play();
        if(bgMusic.src) bgMusic.play();
        
        isPlaying = true;
        updatePlayBtnUI();
    }

    function pauseMeditation() {
        tracks[currentTrackIndex].pause();
        bgMusic.pause();
        isPlaying = false;
        updatePlayBtnUI();
    }

    function updatePlayBtnUI() {
        if (isPlaying) {
            btnPlayPause.innerHTML = '<i class="fa-solid fa-pause"></i>';
        } else {
            btnPlayPause.innerHTML = '<i class="fa-solid fa-play"></i>';
        }
    }

    function updateTrackUI() {
        trackUIs.forEach((ui, index) => {
            if (index === currentTrackIndex) {
                ui.classList.add('active');
            } else {
                ui.classList.remove('active');
            }
        });
    }

    // Track sequential logic
    audioMeditation.addEventListener('ended', () => {
        currentTrackIndex = 1;
        updateTrackUI();
        tracks[currentTrackIndex].play();
    });

    audioSuggestion.addEventListener('ended', () => {
        if (isSuggestionLoop) {
            tracks[currentTrackIndex].play(); // loop itself
        } else {
            currentTrackIndex = 2;
            updateTrackUI();
            tracks[currentTrackIndex].play();
        }
    });

    audioAffirmation.addEventListener('ended', () => {
        if (isAffirmationLoop) {
            tracks[currentTrackIndex].play(); // loop itself
        } else {
            isPlaying = false;
            updatePlayBtnUI();
            bgMusic.pause(); // fade out instead later
        }
    });

    // Loop Toggles
    loopSuggestionBtn.addEventListener('click', () => {
        isSuggestionLoop = !isSuggestionLoop;
        if(isSuggestionLoop) loopSuggestionBtn.classList.add('active');
        else loopSuggestionBtn.classList.remove('active');
    });

    loopAffirmationBtn.addEventListener('click', () => {
        isAffirmationLoop = !isAffirmationLoop;
        if(isAffirmationLoop) loopAffirmationBtn.classList.add('active');
        else loopAffirmationBtn.classList.remove('active');
    });

    // Volume Control
    bgVolume.addEventListener('input', (e) => {
        bgMusic.volume = e.target.value;
    });

    // Restart
    btnRestart.addEventListener('click', () => {
        pauseMeditation();
        tracks.forEach(t => t.currentTime = 0);
        bgMusic.currentTime = 0;
        audioMeditation.src = '';
        audioSuggestion.src = '';
        audioAffirmation.src = '';
        
        stepPlayer.classList.remove('active');
        stepPlayer.classList.add('hidden');
        stepCategory.classList.remove('hidden');
        stepCategory.classList.add('active');
    });
});
