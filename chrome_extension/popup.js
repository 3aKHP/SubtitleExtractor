document.addEventListener('DOMContentLoaded', async () => {
    const urlDisplay = document.getElementById('video-url');
    const extractBtn = document.getElementById('extract-btn');
    const statusDiv = document.getElementById('status');
    const resultContainer = document.getElementById('result-container');
    const mergedContent = document.getElementById('merged-content');
    const ocrContent = document.getElementById('ocr-content');
    const asrContent = document.getElementById('asr-content');
    
    const roiSelect = document.getElementById('roi-select');
    const stepSelect = document.getElementById('step-select');
    const timestampCheck = document.getElementById('timestamp-check');
    const asrCheck = document.getElementById('asr-check');
    const modelSizeSelect = document.getElementById('model-size');
    const downloadBtn = document.getElementById('download-current-btn');

    let [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    let currentResult = null; // 保存当前结果对象
    
    if (tab && tab.url) {
        urlDisplay.textContent = tab.url;
        if (!tab.url.includes('bilibili.com')) {
            statusDiv.textContent = "⚠️ 请在 Bilibili 视频页使用";
            extractBtn.disabled = true;
        }
    }

    // 轮询逻辑
    async function pollStatus(taskId) {
        const intervalId = setInterval(async () => {
            try {
                const res = await fetch(`http://127.0.0.1:8000/status/${taskId}`);
                if (!res.ok) return; // 忽略网络抖动
                
                const data = await res.json();

                if (data.status === 'running') {
                    // 更新进度
                    statusDiv.textContent = `⏳ [${data.progress}%] ${data.message}`;
                    extractBtn.textContent = `处理中 ${data.progress}%`;
                } else if (data.status === 'done') {
                    clearInterval(intervalId);
                    
                    currentResult = data.result;
                    statusDiv.textContent = `✅ 提取成功！标题: ${currentResult.video_title}`;
                    extractBtn.textContent = "再次提取";
                    extractBtn.disabled = false;

                    resultContainer.style.display = 'block';
                    
                    // 填充内容
                    mergedContent.textContent = currentResult.merged_subtitles || "无内容";
                    // ✅ 正确写法 (对应 server.py 的返回键名)
                    ocrContent.textContent = currentResult.ocr_raw || "无内容";
                    asrContent.textContent = currentResult.asr_raw || "无内容";

                    
                    // 默认显示合并结果
                    switchTab('merged-content');
                    
                } else if (data.status === 'error') {
                    clearInterval(intervalId);
                    statusDiv.textContent = `❌ 失败: ${data.error}`;
                    extractBtn.disabled = false;
                    extractBtn.textContent = "重试";
                }
            } catch (err) {
                console.error("Poll error:", err);
            }
        }, 1000); // 每秒轮询一次
    }

    // Tab 切换逻辑
    const tabs = document.querySelectorAll('.tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const targetId = tab.dataset.target;
            switchTab(targetId);
        });
    });

    function switchTab(targetId) {
        // 更新 Tab 状态
        document.querySelectorAll('.tab').forEach(t => {
            t.classList.toggle('active', t.dataset.target === targetId);
        });
        
        // 更新内容显示
        document.querySelectorAll('.tab-content').forEach(c => {
            c.classList.toggle('active', c.id === targetId);
        });
    }

    // 下载按钮逻辑
    downloadBtn.addEventListener('click', () => {
        if (!currentResult) return;
        
        // 获取当前激活的 Tab 内容
        const activeContent = document.querySelector('.tab-content.active');
        const text = activeContent.textContent;
        const type = activeContent.id.replace('-content', ''); // merged, ocr, asr
        
        const safeTitle = currentResult.video_title.replace(/[\/:*?"<>|]/g, "_");
        downloadString(text, "text/plain", `subtitle_${safeTitle}_${type}.txt`);
    });

    extractBtn.addEventListener('click', async () => {
        const videoUrl = tab.url;
        const roi = parseFloat(roiSelect.value);
        const step = parseInt(stepSelect.value);
        const timestamp = timestampCheck.checked;
        const enableAsr = asrCheck.checked;
        const modelSize = modelSizeSelect.value;

        extractBtn.disabled = true;
        extractBtn.textContent = "正在提交...";
        statusDiv.textContent = "⏳ 正在连接服务器...";
        resultContainer.style.display = 'none';

        try {
            const response = await fetch('http://127.0.0.1:8000/extract', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    url: videoUrl,
                    roi: roi,
                    step: step,
                    timestamp: timestamp,
                    enable_asr: enableAsr,
                    model_size: modelSize
                })
            });

            if (!response.ok) throw new Error("提交失败");

            const data = await response.json();
            // 拿到 task_id，开始轮询
            pollStatus(data.task_id);

        } catch (error) {
            console.error(error);
            statusDiv.textContent = `❌ 错误: ${error.message}`;
            extractBtn.disabled = false;
            extractBtn.textContent = "重试";
        }
    });
});

function downloadString(text, fileType, fileName) {
    var blob = new Blob([text], { type: fileType });
    var a = document.createElement('a');
    a.download = fileName;
    a.href = URL.createObjectURL(blob);
    a.dataset.downloadurl = [fileType, a.download, a.href].join(':');
    a.style.display = "none";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(function() { URL.revokeObjectURL(a.href); }, 1500);
}
