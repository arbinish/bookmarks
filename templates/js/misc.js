var sorted_data = data.sort(function customSort(a, b) {
    return parseInt(a.count) < parseInt(b.count) ? 1:-1
}
