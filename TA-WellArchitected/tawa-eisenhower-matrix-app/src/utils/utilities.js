export const replaceHtmlTags = (text) => {
    text = text.replace(/\s?(<h4 class='headerBodyStyle'>)\s?/g, "");
    text = text.replace(/\s?(<\/h4>)\s?/g, "");
    text = text.replace(/\s?(<br\s?\/?>)\s?/g, "\r\n");
    return text
}

export const copyToClipboard = (text) => {
    // get currently selected element
    const selected = document.getSelection().rangeCount > 0 ? document.getSelection().getRangeAt(0) : false;
    const textArea = document.createElement('textarea');
    textArea.textContent = text;
    document.body.appendChild(textArea);
    textArea.select();
    try {
        document.execCommand('copy');
    } catch (err) {
        /* tslint:disable-next-line:no-console */
        console.error('Unable to copy:', err);
    }
    textArea.remove();
    if (selected) {
        // if there was an element selected, re-select it
        document.getSelection().removeAllRanges();
        document.getSelection().addRange(selected);
    }
};