import React, { useState, useRef, useEffect } from "react";
import axios from "axios";
import { useTheme } from "../context/ThemeContext";
import config from "../config";
import "./AIChat.css";

function AIChat({ onAnalysisUpdate, onClose, isFloating = false }) {
  const { isDarkMode } = useTheme();
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        '👋 Hi! I\'m your AI analysis assistant. Ask me to analyze data, generate insights, or create custom visualizations. For example:\n\n• "Show me the most negative topics this week"\n• "Compare sentiment trends for innovation and belonging"\n• "What are the top concerns this month?"\n• "Generate insights for the last 7 days"',
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const chatRef = useRef(null);
  // Initial position for the floating chat window with immediate parent container constraints
  const [position, setPosition] = useState(() => {
    const margin = 20;
    const defaultWidth = 400;
    const defaultHeight = 500;

    // Get parent container (analysis-ai) dimensions if available
    const parent = document.querySelector(".analysis-ai");

    // 因为我们使用right属性定位，所以x值应该是从右侧的偏移量
    // 较小的值意味着更靠右
    let rightOffset = margin; // 默认为最右侧

    if (parent) {
      const parentRect = parent.getBoundingClientRect();
      // 确保偏移量在有效范围内
      const maxRightOffset = parentRect.width - defaultWidth - margin;
      rightOffset = Math.min(rightOffset, maxRightOffset);
    }

    // Calculate a safe initial position that stays within parent container
    return {
      x: rightOffset, // 使用右侧偏移量，较小的值意味着更靠右
      y: margin, // Start from top with margin
    };
  });
  const [isDragging, setIsDragging] = useState(false);
  const dragStartPos = useRef(null);
  const dragStartMouse = useRef(null);

  // Initialize position when floating window opens
  useEffect(() => {
    if (isFloating && position === null) {
      // 获取父容器（analysis-ai）尺寸
      const parent = document.querySelector(".analysis-ai");
      const margin = 20;
      const defaultWidth = 400;
      const defaultHeight = 500;

      // 优先从父容器获取宽度，如果没有则使用视口宽度
      let availableWidth = window.innerWidth;
      if (parent) {
        availableWidth = parent.getBoundingClientRect().width;
      }

      // 计算右侧位置 - 由于我们使用right属性，这里设置一个较小的值意味着更靠右
      let x = margin;

      const y = margin; // 顶部位置

      setPosition({ x, y });
    } else if (!isFloating && position !== null) {
      // Reset position when closing
      setPosition(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isFloating]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Drag functionality
  useEffect(() => {
    if (!isFloating || !isDragging) return;

    const handleMouseMove = (e) => {
      if (
        !isDragging ||
        !dragStartPos.current ||
        !dragStartMouse.current ||
        !chatRef.current
      )
        return;

      // Calculate new position - 注意：当使用right属性时，x方向需要反转
      const dx = e.clientX - dragStartMouse.current.x;
      const dy = e.clientY - dragStartMouse.current.y;

      // 反转x方向移动，确保鼠标向左拖动时窗口也向左移动
      let newX = dragStartPos.current.x - dx;
      let newY = dragStartPos.current.y + dy;

      // Apply constraints based on parent container
      const constrainedPos = constrainPosition(newX, newY);

      setPosition(constrainedPos);
    };

    const handleMouseUp = () => {
      setIsDragging(false);
    };

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
    // Prevent text selection while dragging
    document.body.style.userSelect = "none";
    document.body.style.cursor = "grabbing";

    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
      document.body.style.userSelect = "";
      document.body.style.cursor = "";
    };
  }, [isDragging, isFloating]);

  // Function to constrain position within parent container (analysis-ai)
  const constrainPosition = (x, y) => {
    const margin = 20;
    const defaultWidth = 400;
    const defaultHeight = 500;
    const chatWidth = chatRef.current
      ? chatRef.current.offsetWidth
      : defaultWidth;
    const chatHeight = chatRef.current
      ? chatRef.current.offsetHeight
      : defaultHeight;

    // Get parent container (analysis-ai) instead of viewport
    const parent = document.querySelector(".analysis-ai");
    let maxRightOffset = 0; // 最大右侧偏移量（最小right值，最靠右）
    let minRightOffset = 100; // 最小右侧偏移量（最大right值，最靠左）
    let maxY = 100; // Default fallback for Y

    if (parent) {
      const parentRect = parent.getBoundingClientRect();
      // 计算可允许的最小right偏移量（最靠左的位置）
      minRightOffset = parentRect.width - chatWidth - margin;
      maxY = parentRect.height - chatHeight - margin;
    }

    // 确保right偏移量在有效范围内
    // 注意：由于我们使用right属性定位，较小的值意味着更靠右
    const constrainedX = Math.max(
      maxRightOffset + margin,
      Math.min(x, minRightOffset)
    );

    return {
      x: constrainedX,
      y: Math.max(margin, Math.min(y, maxY)),
    };
  };

  // Initialize position when floating mode is activated
  useEffect(() => {
    if (!isFloating) return;

    // Only set initial position if not already set
    if (!position) {
      // Set default position on right side with constraints
      const margin = 20;

      // 因为我们使用right属性定位，设置一个小的值将窗口放在右侧
      // 较小的right偏移量意味着更靠右
      const defaultX = margin;
      const defaultY = 20; // Top position with margin

      const constrainedPos = constrainPosition(defaultX, defaultY);
      setPosition(constrainedPos);
    }
  }, [isFloating]); // 移除任何可能导致无限循环的依赖

  // Handle window resize to keep chat window within parent container
  useEffect(() => {
    if (!isFloating || !chatRef.current) return;

    const handleResize = () => {
      // Use our constrainPosition function that works with parent container
      if (position) {
        const constrainedPos = constrainPosition(position.x, position.y);
        // Only update if position needs to be constrained
        if (
          constrainedPos.x !== position.x ||
          constrainedPos.y !== position.y
        ) {
          setPosition(constrainedPos);
        }
      }
    };

    // Run once immediately to ensure initial position is constrained
    handleResize();

    // Add resize event listener
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [isFloating]); // Removed position from dependencies to prevent infinite loop

  // Safety check on component mount and when parent container might change
  useEffect(() => {
    // Apply constraints on component mount
    const checkAndConstrainPosition = () => {
      if (isFloating && position) {
        const constrainedPos = constrainPosition(position.x, position.y);
        // Only update if position has changed
        if (
          constrainedPos.x !== position.x ||
          constrainedPos.y !== position.y
        ) {
          setPosition(constrainedPos);
        }
      }
    };

    checkAndConstrainPosition();

    // Set up MutationObserver to detect changes in parent container size
    const observer = new MutationObserver(() => {
      checkAndConstrainPosition();
    });

    // Observe the parent container (analysis-ai)
    const parent = document.querySelector(".analysis-ai");
    if (parent) {
      observer.observe(parent, {
        attributes: true,
        childList: true,
        subtree: true,
      });
    }

    return () => {
      observer.disconnect();
    };
  }, [isFloating]); // Removed position from dependencies to prevent infinite loop


  const handleMouseDown = (e) => {
    if (!isFloating || !chatRef.current || !position) return;

    // Only allow dragging from header, not from buttons
    if (e.target.closest("button")) {
      return;
    }

    e.preventDefault();
    e.stopPropagation();

    dragStartPos.current = {
      x: position.x,
      y: position.y,
    };
    dragStartMouse.current = {
      x: e.clientX,
      y: e.clientY,
    };
    setIsDragging(true);
  };

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMessage = {
      role: "user",
      content: input.trim(),
    };

    // Add user message to state first for immediate UI update
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      // Send conversation history BEFORE adding the current message to avoid duplication
      // Include last 5 messages (excluding the one we just added)
      const historyForContext = messages.slice(-5);

      const response = await axios.post(
        `${config.API_URL}/api/ai-analysis/chat`,
        {
          message: userMessage.content,
          conversation_history: historyForContext, // Send previous messages for context
        }
      );

      const assistantMessage = {
        role: "assistant",
        content: response.data.response,
        analysisData: response.data.analysis_data,
        visualizationConfig: response.data.visualization_config,
        aiInsights: response.data.ai_insights || [],
        aiSummary: response.data.ai_summary || "",
      };

      setMessages((prev) => [...prev, assistantMessage]);

      // Trigger page update if analysis data is provided
      // COMMENTED OUT: Disable page view switching after chat bot queries
      // if (response.data.analysis_data && onAnalysisUpdate) {
      //   onAnalysisUpdate(response.data.analysis_data, response.data.visualization_config);
      // }
    } catch (error) {
      console.error("Error sending message:", error);
      const errorMessage = {
        role: "assistant",
        content:
          "Sorry, I encountered an error processing your request. Please try again.",
        error: true,
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const clearChat = () => {
    setMessages([
      {
        role: "assistant",
        content: "👋 Chat cleared! How can I help you analyze your data today?",
      },
    ]);
  };

  const chatClassName = `ai-chat ${isDarkMode ? "dark" : ""} ${
    isFloating ? "floating" : ""
  }`;
  const chatStyle =
    isFloating && position
      ? {
          position: "absolute",
          right: `${position.x}px`,
          top: `${position.y}px`,
          zIndex: 1000,
          // Allow dynamic sizing
          boxShadow:
            "0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)",
        }
      : {};

  return (
    <div ref={chatRef} className={chatClassName} style={chatStyle}>
      <div
        className="chat-header"
        onMouseDown={handleMouseDown}
        style={{
          cursor: isFloating ? (isDragging ? "grabbing" : "grab") : "default",
        }}
      >
        <div className="chat-title">
          <span className="chat-icon">🤖</span>
          <h3>AI Analysis Assistant</h3>
        </div>
        <div className="header-actions">
          <button className="clear-btn" onClick={clearChat} title="Clear chat">
            🗑️
          </button>
          {isFloating && onClose && (
            <button className="close-btn" onClick={onClose} title="Close">
              ✕
            </button>
          )}
        </div>
      </div>

      <div className="chat-messages">
        {messages.map((message, index) => (
          <div key={index} className={`message ${message.role}`}>
            <div className="message-avatar">
              {message.role === "user" ? "👤" : "🤖"}
            </div>
            <div className="message-content">
              <div className="message-text">
                {message.content.split("\n").map((line, i) => {
                  // Handle headings
                  if (line.startsWith("## ")) {
                    return (
                      <h3 key={i} className="message-heading">
                        {line.replace("## ", "")}
                      </h3>
                    );
                  }

                  // Handle empty lines
                  if (line.trim() === "") {
                    return <br key={i} />;
                  }

                  // Process inline markdown formatting (bold, italic, etc.)
                  const processInlineMarkdown = (text) => {
                    const parts = [];
                    let lastIndex = 0;
                    // Match **bold** or *italic*
                    const markdownRegex =
                      /(\*\*([^*]+)\*\*|\*([^*]+)\*|`([^`]+)`)/g;
                    let match;

                    while ((match = markdownRegex.exec(text)) !== null) {
                      // Add text before the match
                      if (match.index > lastIndex) {
                        parts.push(text.substring(lastIndex, match.index));
                      }

                      // Add the formatted content
                      if (
                        match[1].startsWith("**") &&
                        match[1].endsWith("**")
                      ) {
                        // Bold: **text**
                        parts.push(
                          <strong key={`bold-${match.index}`}>
                            {match[2]}
                          </strong>
                        );
                      } else if (
                        match[1].startsWith("*") &&
                        match[1].endsWith("*") &&
                        !match[1].startsWith("**")
                      ) {
                        // Italic: *text*
                        parts.push(
                          <em key={`italic-${match.index}`}>{match[3]}</em>
                        );
                      } else if (
                        match[1].startsWith("`") &&
                        match[1].endsWith("`")
                      ) {
                        // Code: `text`
                        parts.push(
                          <code key={`code-${match.index}`}>{match[4]}</code>
                        );
                      }

                      lastIndex = match.index + match[0].length;
                    }

                    // Add remaining text
                    if (lastIndex < text.length) {
                      parts.push(text.substring(lastIndex));
                    }

                    // If no markdown was found, return original text
                    return parts.length > 0 ? parts : text;
                  };

                  // Handle numbered lists
                  if (line.match(/^\d+\./)) {
                    return (
                      <div key={i} className="message-list-item">
                        {processInlineMarkdown(line)}
                      </div>
                    );
                  }

                  // Handle bullet points
                  if (line.match(/^[-•]\s/)) {
                    return (
                      <div key={i} className="message-list-item">
                        {processInlineMarkdown(line)}
                      </div>
                    );
                  }

                  // Process regular line with inline markdown
                  const processedLine = processInlineMarkdown(line);
                  return (
                    <React.Fragment key={i}>
                      {processedLine}
                      {i < message.content.split("\n").length - 1 && <br />}
                    </React.Fragment>
                  );
                })}
              </div>
              {message.aiInsights && message.aiInsights.length > 0 && (
                <div className="ai-insights-preview">
                  <div className="insights-header">✨ AI Insights:</div>
                  {message.aiInsights.slice(0, 3).map((insight, idx) => (
                    <div key={idx} className="insight-preview-item">
                      <span
                        className={`importance-badge ${
                          insight.importance || "medium"
                        }`}
                      >
                        {insight.importance === "high"
                          ? "🔴"
                          : insight.importance === "low"
                          ? "🟢"
                          : "🟡"}
                      </span>
                      <strong>{insight.title || "Insight"}</strong>
                    </div>
                  ))}
                  {message.aiInsights.length > 3 && (
                    <div className="insights-more">
                      + {message.aiInsights.length - 3} more insights in
                      analysis view
                    </div>
                  )}
                </div>
              )}
              {message.error && (
                <div className="message-error">
                  ⚠️ Please check your request and try again
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="message assistant">
            <div className="message-avatar">🤖</div>
            <div className="message-content">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-container">
        <textarea
          className="chat-input"
          placeholder="Ask me to analyze your data..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          rows={2}
          disabled={loading}
        />
        <button
          className="send-btn"
          onClick={handleSend}
          disabled={!input.trim() || loading}
        >
          {loading ? "⏳" : "📤"}
        </button>
      </div>

      <div className="chat-suggestions">
        <div className="suggestions-label">Quick suggestions:</div>
        <div className="suggestions-list">
          {[
            "Show negative topics",
            "Compare themes",
            "Last 7 days analysis",
            "Generate insights",
          ].map((suggestion, index) => (
            <button
              key={index}
              className="suggestion-btn"
              onClick={() => {
                setInput(suggestion);
                setTimeout(() => handleSend(), 100);
              }}
              disabled={loading}
            >
              {suggestion}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

export default AIChat;
