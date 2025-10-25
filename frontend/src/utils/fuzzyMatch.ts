/**
 * Fuzzy matching utilities for file search
 * Implements client-side fuzzy search with highlighting
 */

export interface FuzzyMatchResult {
  matches: boolean
  score: number
  highlights: number[] // Indices of matched characters
}

/**
 * Perform fuzzy matching on a string
 *
 * @param query - Search query
 * @param text - Text to search in
 * @param caseSensitive - Whether matching should be case-sensitive (default: false)
 * @returns Match result with score and highlighted character indices
 */
export const fuzzyMatch = (
  query: string,
  text: string,
  caseSensitive: boolean = false
): FuzzyMatchResult => {
  if (!query) {
    return { matches: true, score: 0, highlights: [] }
  }

  const searchText = caseSensitive ? text : text.toLowerCase()
  const searchQuery = caseSensitive ? query : query.toLowerCase()

  const highlights: number[] = []
  let queryIndex = 0
  let score = 0
  let consecutive = 0
  let previousMatchIndex = -1

  for (let i = 0; i < searchText.length && queryIndex < searchQuery.length; i++) {
    if (searchText[i] === searchQuery[queryIndex]) {
      highlights.push(i)

      // Base score for match
      score += 10

      // Bonus for consecutive characters
      if (previousMatchIndex === i - 1) {
        consecutive++
        score += consecutive * 5
      } else {
        consecutive = 0
      }

      // Bonus for match at word boundary
      if (i === 0 || /\s|[-_/]/.test(searchText[i - 1])) {
        score += 15
      }

      // Bonus for exact case match (even in case-insensitive mode)
      if (text[i] === query[queryIndex]) {
        score += 2
      }

      previousMatchIndex = i
      queryIndex++
    }
  }

  const matches = queryIndex === searchQuery.length

  // Penalty for length difference
  if (matches) {
    const lengthDiff = text.length - query.length
    score -= lengthDiff * 0.5

    // Bonus for shorter strings (more relevant)
    if (text.length < 50) {
      score += 10
    }
  }

  return { matches, score, highlights }
}

/**
 * Highlight matched characters in text
 *
 * @param text - Original text
 * @param highlights - Array of character indices to highlight
 * @returns Array of text segments with highlight flags
 */
export interface HighlightedSegment {
  text: string
  highlighted: boolean
}

export const getHighlightedSegments = (
  text: string,
  highlights: number[]
): HighlightedSegment[] => {
  if (highlights.length === 0) {
    return [{ text, highlighted: false }]
  }

  const segments: HighlightedSegment[] = []
  let currentSegment = ''
  let isHighlighted = false

  for (let i = 0; i < text.length; i++) {
    const shouldHighlight = highlights.includes(i)

    if (shouldHighlight !== isHighlighted) {
      // State change - push current segment
      if (currentSegment) {
        segments.push({ text: currentSegment, highlighted: isHighlighted })
      }
      currentSegment = text[i]
      isHighlighted = shouldHighlight
    } else {
      currentSegment += text[i]
    }
  }

  // Push final segment
  if (currentSegment) {
    segments.push({ text: currentSegment, highlighted: isHighlighted })
  }

  return segments
}

/**
 * Sort items by fuzzy match score
 *
 * @param items - Array of items to sort
 * @param query - Search query
 * @param getText - Function to extract searchable text from item
 * @returns Sorted array with match scores
 */
export const fuzzySort = <T>(
  items: T[],
  query: string,
  getText: (item: T) => string
): Array<T & { __fuzzyScore: number; __fuzzyHighlights: number[] }> => {
  if (!query) {
    return items.map(item => ({
      ...item,
      __fuzzyScore: 0,
      __fuzzyHighlights: []
    }))
  }

  const scored = items
    .map(item => {
      const text = getText(item)
      const result = fuzzyMatch(query, text)
      return {
        ...item,
        __fuzzyScore: result.matches ? result.score : -1,
        __fuzzyHighlights: result.highlights
      }
    })
    .filter(item => item.__fuzzyScore >= 0)

  // Sort by score descending
  scored.sort((a, b) => b.__fuzzyScore - a.__fuzzyScore)

  return scored
}

/**
 * Filter and rank file paths by fuzzy match
 *
 * @param paths - Array of file paths
 * @param query - Search query
 * @returns Filtered and sorted paths with match info
 */
export interface FuzzyFileMatch {
  path: string
  score: number
  highlights: number[]
  nameHighlights: number[]
  pathHighlights: number[]
}

export const fuzzyFilterPaths = (paths: string[], query: string): FuzzyFileMatch[] => {
  if (!query) {
    return paths.map(path => ({
      path,
      score: 0,
      highlights: [],
      nameHighlights: [],
      pathHighlights: []
    }))
  }

  const results: FuzzyFileMatch[] = []

  for (const path of paths) {
    const fileName = path.split('/').pop() || path
    const nameResult = fuzzyMatch(query, fileName)
    const pathResult = fuzzyMatch(query, path)

    // Calculate combined score (prioritize filename matches)
    let score = 0
    let highlights: number[] = []

    if (nameResult.matches) {
      score = nameResult.score * 2 // Filename matches worth 2x
      highlights = nameResult.highlights.map(i => path.length - fileName.length + i)
    } else if (pathResult.matches) {
      score = pathResult.score
      highlights = pathResult.highlights
    }

    if (score > 0) {
      results.push({
        path,
        score,
        highlights,
        nameHighlights: nameResult.highlights,
        pathHighlights: pathResult.highlights
      })
    }
  }

  // Sort by score descending
  results.sort((a, b) => b.score - a.score)

  return results
}

/**
 * Debounce function for search input
 *
 * @param func - Function to debounce
 * @param wait - Wait time in milliseconds
 * @returns Debounced function
 */
export const debounce = <T extends (...args: any[]) => any>(
  func: T,
  wait: number
): ((...args: Parameters<T>) => void) => {
  let timeout: NodeJS.Timeout | null = null

  return (...args: Parameters<T>) => {
    if (timeout) {
      clearTimeout(timeout)
    }

    timeout = setTimeout(() => {
      func(...args)
    }, wait)
  }
}
