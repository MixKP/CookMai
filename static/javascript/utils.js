const parseArray = (str) => {
    if (!str || str === 'character(0)') return [];
    try {
        let cleaned = str.replace(/^c\(/, '').replace(/\)$/, '');
        let matches = [...cleaned.matchAll(/"([^"]+)"|'([^']+)'/g)];
        return matches.map(m => m[1] || m[2]);
    } catch (e) { return [str]; }
};

const getImage = (str) => {
    // Handle plain URL string (from ImageCollection)
    if (str && str.startsWith('http')) return str;

    // Handle R array format: c("url1", "url2")
    const arr = parseArray(str);
    if (arr.length && arr[0].startsWith('http')) return arr[0];

    return '/static/images/no-image.jpg';
};