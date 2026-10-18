
document.addEventListener("DOMContentLoaded", () => {
    const chatForm = document.getElementById("chat-form");
    const chatOutput = document.getElementById("chat-output");
    const messageInput = document.getElementById("message-input");
    const micButton = document.getElementById("mic-button");
    const stopButton = document.getElementById("stop-speaking-button");
    const sendButton = document.getElementById("send-button");
    const voiceStatus = document.getElementById("voice-status");

    const newChatButton = document.getElementById("new-chat-button");
    const welcomeScreen = document.getElementById("welcome-screen");
    const sidebar = document.getElementById("sidebar");
    const openSidebarButton = document.getElementById("open-sidebar");
    const closeSidebarButton = document.getElementById("close-sidebar");
    const sidebarHistory = document.getElementById("sidebar-history");

    if (!chatForm || !chatOutput || !messageInput) return;

    let recognition = null;
    let isListening = false;
    let isSpeaking = false;
    let isSending = false;
    let currentChatMessages = [];

    function setStatus(message) {
        if (voiceStatus) voiceStatus.textContent = message;
    }

    function formatTime() {
        return new Date().toLocaleString("en-IN", {
            day: "2-digit",
            month: "short",
            year: "numeric",
            hour: "2-digit",
            minute: "2-digit"
        });
    }

    function scrollToBottom() {
        chatOutput.scrollTop = chatOutput.scrollHeight;
    }

    function addMessage(sender, text, timestamp = "") {
        const wrapper = document.createElement("div");

        wrapper.className = sender === "You"
            ? "message user-message"
            : "message bot-message";

        const label = document.createElement("div");
        label.className = "message-label";
        label.textContent = sender;

        const content = document.createElement("div");
        content.className = "message-content";
        content.textContent = text;

        wrapper.appendChild(label);
        wrapper.appendChild(content);

        const timeText = timestamp || formatTime();
        const time = document.createElement("div");
        time.className = "message-time";
        time.textContent = timeText;
        wrapper.appendChild(time);

        chatOutput.appendChild(wrapper);
        scrollToBottom();

        return wrapper;
    }

    function showWelcome(show) {
        if (welcomeScreen) {
            welcomeScreen.style.display = show ? "block" : "none";
        }
    }

    function stopAssistantVoice() {
        if ("speechSynthesis" in window) {
            window.speechSynthesis.cancel();
        }

        isSpeaking = false;
        setStatus("Voice stopped. You are in control. 💜");
    }

    function speakText(text) {
        if (!("speechSynthesis" in window)) {
            setStatus("Voice output is not supported in this browser.");
            return;
        }

        const spokenText = text
            .replace(/https?:\/\/\S+/g, "")
            .replace(/\nSources:[\s\S]*/i, "")
            .trim();

        if (!spokenText) return;

        window.speechSynthesis.cancel();

        const utterance = new SpeechSynthesisUtterance(spokenText);
        utterance.lang = "en-IN";
        utterance.rate = 1.1;
        utterance.pitch = 1;

        utterance.onstart = () => {
            isSpeaking = true;
            setStatus("Hub-Bot is speaking...");
        };

        utterance.onend = () => {
            isSpeaking = false;
            setStatus("Ready when you are.");
        };

        utterance.onerror = (event) => {
            isSpeaking = false;

            if (
                event.error !== "canceled" &&
                event.error !== "interrupted"
            ) {
                setStatus("Voice playback stopped.");
            }
        };

        window.speechSynthesis.speak(utterance);
    }

    // Load saved messages from Django/PostgreSQL.
    async function loadChatHistory() {
        const historyUrl = chatForm.dataset.historyUrl;

        if (!historyUrl) {
            setStatus("Ready when you are.");
            return;
        }

        try {
            setStatus("Loading previous conversations...");

            const response = await fetch(historyUrl, {
                method: "GET",
                headers: { "Accept": "application/json" },
                credentials: "same-origin"
            });

            if (!response.ok) {
                throw new Error("Could not load chat history.");
            }

            const data = await response.json();
            const messages = data.messages || [];

            // Do not overwrite a new chat the user has already started.
            if (currentChatMessages.length > 0) return;

            chatOutput.replaceChildren();
            currentChatMessages = messages.map(message => ({
                role: message.role,
                content: message.content,
                created_at: message.created_at || ""
            }));

            messages.forEach(message => {
                addMessage(
                    message.role === "user" ? "You" : "Hub-Bot",
                    message.content,
                    message.created_at || ""
                );
            });

            showWelcome(messages.length === 0);
            renderSidebarHistory(messages);

            setStatus(
                messages.length
                    ? "Previous conversations loaded."
                    : "Start a new conversation! 💜"
            );
        } catch (error) {
            console.error("Chat history error:", error);
            setStatus("Could not load chat history. You can still chat.");
            renderSidebarHistory([]);
        }
    }

    // Show recent messages in the sidebar.
    // Note: this is a recent-message preview, not separate conversations.
    function renderSidebarHistory(messages) {
        if (!sidebarHistory) return;

        sidebarHistory.replaceChildren();

        if (!messages.length) {
            const empty = document.createElement("p");
            empty.className = "history-empty";
            empty.textContent = "No messages yet. Start a new chat!";
            sidebarHistory.appendChild(empty);
            return;
        }

        const groups = [];
        let currentGroup = [];

        messages.forEach(message => {
            if (message.role === "user") {
                if (currentGroup.length) groups.push(currentGroup);
                currentGroup = [message];
            } else {
                currentGroup.push(message);
            }
        });

        if (currentGroup.length) groups.push(currentGroup);

        groups.slice().reverse().forEach(group => {
            const firstMessage = group[0];
            const preview = document.createElement("button");

            preview.type = "button";
            preview.className = "history-item";
            preview.textContent = firstMessage.content.length > 28
                ? firstMessage.content.slice(0, 28) + "…"
                : firstMessage.content;

            preview.title = firstMessage.content;

            preview.addEventListener("click", () => {
                chatOutput.replaceChildren();
                showWelcome(false);

                group.forEach(message => {
                    addMessage(
                        message.role === "user" ? "You" : "Hub-Bot",
                        message.content,
                        message.created_at || ""
                    );
                });

                currentChatMessages = group.slice();

                if (sidebar) sidebar.classList.remove("open");
                setStatus("Showing selected messages.");
            });

            sidebarHistory.appendChild(preview);
        });
    }

    // New Chat clears only the current view.
    // It does NOT delete PostgreSQL history.
    function startNewChat() {
        if (isSending) {
            setStatus("Please wait for the current response to finish.");
            return;
        }

        stopAssistantVoice();

        if (recognition && isListening) {
            recognition.stop();
        }

        currentChatMessages = [];
        chatOutput.replaceChildren();
        messageInput.value = "";

        showWelcome(true);
        messageInput.focus();

        if (sidebar) sidebar.classList.remove("open");

        setStatus("New chat started. What would you like to ask? 💜");
    }

    if (newChatButton) {
        newChatButton.addEventListener("click", startNewChat);
    }

    // Mobile sidebar controls.
    if (openSidebarButton && sidebar) {
        openSidebarButton.addEventListener("click", () => {
            sidebar.classList.add("open");
        });
    }

    if (closeSidebarButton && sidebar) {
        closeSidebarButton.addEventListener("click", () => {
            sidebar.classList.remove("open");
        });
    }

    // Suggestion cards fill the composer.
    document.querySelectorAll(".suggestion-card").forEach(card => {
        card.addEventListener("click", () => {
            messageInput.value = card.dataset.prompt || "";
            messageInput.focus();
        });
    });

    async function sendMessage(message) {
        const text = message.trim();

        if (!text || isSending) return;

        stopAssistantVoice();
        showWelcome(false);

        currentChatMessages.push({
            role: "user",
            content: text,
            created_at: formatTime()
        });

        addMessage("You", text);

        messageInput.value = "";
        messageInput.focus();
        isSending = true;

        if (sendButton) {
            sendButton.disabled = true;
            sendButton.textContent = "…";
        }

        if (newChatButton) newChatButton.disabled = true;

        setStatus("Hub-Bot is thinking...");

        try {
            const csrfInput = chatForm.querySelector(
                'input[name="csrfmiddlewaretoken"]'
            );

            const response = await fetch(chatForm.dataset.chatUrl, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrfInput ? csrfInput.value : ""
                },
                credentials: "same-origin",
                body: JSON.stringify({ message: text })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || "Request failed.");
            }

            const reply = data.reply || data.error ||
                "I couldn't generate a response.";

            currentChatMessages.push({
                role: "assistant",
                content: reply,
                created_at: formatTime()
            });

            addMessage("Hub-Bot", reply);
            renderSidebarHistory(currentChatMessages);
            speakText(reply);

        } catch (error) {
            addMessage(
                "Hub-Bot",
                error.message || "Something went wrong. Please try again."
            );
            setStatus("Unable to get a response.");
        } finally {
            isSending = false;

            if (sendButton) {
                sendButton.disabled = false;
                sendButton.textContent = "↑";
            }

            if (newChatButton) newChatButton.disabled = false;
        }
    }

    chatForm.addEventListener("submit", event => {
        event.preventDefault();
        sendMessage(messageInput.value);
    });

    messageInput.addEventListener("keydown", event => {
        if (
            event.key === "Enter" &&
            !event.shiftKey &&
            !event.isComposing
        ) {
            event.preventDefault();
            chatForm.requestSubmit();
        }
    });

    if (stopButton) {
        stopButton.addEventListener("click", stopAssistantVoice);
    }

    window.addEventListener("pagehide", () => {
        if ("speechSynthesis" in window) {
            window.speechSynthesis.cancel();
        }
    });

    const SpeechRecognition =
        window.SpeechRecognition || window.webkitSpeechRecognition;

    if (SpeechRecognition) {
        recognition = new SpeechRecognition();
        recognition.lang = "en-IN";
        recognition.continuous = false;
        recognition.interimResults = false;

        recognition.onstart = () => {
            isListening = true;

            if (micButton) micButton.textContent = "🔴";

            setStatus("Listening. Speak now...");
        };

        recognition.onresult = event => {
            messageInput.value = event.results[0][0].transcript;
            messageInput.focus();
            setStatus("Voice captured. Press Send to submit.");
        };

        recognition.onerror = event => {
            setStatus("Voice input error: " + event.error);
        };

        recognition.onend = () => {
            isListening = false;

            if (micButton) micButton.textContent = "🎙";
        };

        if (micButton) {
            micButton.addEventListener("click", () => {
                if (isListening) {
                    recognition.stop();
                    return;
                }

                try {
                    recognition.start();
                } catch (error) {
                    setStatus("Microphone is busy. Please try again.");
                }
            });
        }
    } else {
        if (micButton) {
            micButton.disabled = true;
            micButton.title = "Voice input is not supported in this browser.";
        }

        setStatus("Voice input is not supported. You can still type.");
    }

    loadChatHistory();
});
