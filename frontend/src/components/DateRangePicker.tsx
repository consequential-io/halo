import { useState, useRef, useEffect } from 'react'

interface DateRangePickerProps {
  startDate: Date
  endDate: Date
  onChange: (start: Date, end: Date) => void
}

const styles = {
  container: {
    position: 'relative' as const,
  },
  trigger: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    padding: '10px 16px',
    background: '#1A1A1A',
    border: '1px solid rgba(255,255,255,0.2)',
    borderRadius: '8px',
    cursor: 'pointer',
    color: '#FFFFFF',
    fontSize: '14px',
    minWidth: '220px',
  },
  calendarIcon: {
    color: '#A1A1A1',
  },
  dropdown: {
    position: 'absolute' as const,
    top: '100%',
    right: 0,
    marginTop: '8px',
    background: '#1A1A1A',
    border: '1px solid rgba(255,255,255,0.1)',
    borderRadius: '12px',
    boxShadow: '0 10px 40px rgba(0,0,0,0.5)',
    zIndex: 1000,
    padding: '20px',
    minWidth: '600px',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '16px',
  },
  navBtn: {
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    padding: '8px',
    color: '#A1A1A1',
    fontSize: '18px',
    transition: 'color 0.2s',
  },
  title: {
    fontSize: '16px',
    fontWeight: 600,
    color: '#FFFFFF',
  },
  calendars: {
    display: 'flex',
    gap: '32px',
  },
  calendar: {
    flex: 1,
  },
  monthTitle: {
    textAlign: 'center' as const,
    fontSize: '14px',
    fontWeight: 600,
    color: '#FFFFFF',
    marginBottom: '12px',
  },
  weekdays: {
    display: 'grid',
    gridTemplateColumns: 'repeat(7, 1fr)',
    gap: '4px',
    marginBottom: '8px',
  },
  weekday: {
    textAlign: 'center' as const,
    fontSize: '12px',
    color: '#666',
    fontWeight: 500,
    padding: '4px',
  },
  days: {
    display: 'grid',
    gridTemplateColumns: 'repeat(7, 1fr)',
    gap: '2px',
  },
  day: {
    width: '36px',
    height: '36px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '14px',
    borderRadius: '6px',
    cursor: 'pointer',
    border: 'none',
    background: 'transparent',
    color: '#E0E0E0',
    transition: 'all 0.15s ease',
  },
  dayHover: {
    background: 'rgba(154, 230, 92, 0.1)',
  },
  dayDisabled: {
    color: '#444',
    cursor: 'default',
  },
  daySelected: {
    background: '#9AE65C',
    color: '#0A0A0A',
    fontWeight: 600,
  },
  dayInRange: {
    background: 'rgba(154, 230, 92, 0.2)',
    color: '#9AE65C',
    borderRadius: '0',
  },
  dayRangeStart: {
    borderTopLeftRadius: '6px',
    borderBottomLeftRadius: '6px',
    borderTopRightRadius: '0',
    borderBottomRightRadius: '0',
  },
  dayRangeEnd: {
    borderTopRightRadius: '6px',
    borderBottomRightRadius: '6px',
    borderTopLeftRadius: '0',
    borderBottomLeftRadius: '0',
  },
  dayToday: {
    border: '1px solid #9AE65C',
  },
  footer: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: '16px',
    paddingTop: '16px',
    borderTop: '1px solid rgba(255,255,255,0.1)',
  },
  clearBtn: {
    padding: '8px 16px',
    background: 'rgba(255,255,255,0.05)',
    border: '1px solid rgba(255,255,255,0.2)',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '14px',
    color: '#A1A1A1',
    transition: 'all 0.2s',
  },
  doneBtn: {
    padding: '8px 20px',
    background: '#9AE65C',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '14px',
    color: '#0A0A0A',
    fontWeight: 600,
    transition: 'all 0.2s',
  },
  doneBtnDisabled: {
    background: 'rgba(154, 230, 92, 0.3)',
    cursor: 'not-allowed',
  },
  quickSelect: {
    display: 'flex',
    gap: '8px',
    marginBottom: '16px',
    flexWrap: 'wrap' as const,
  },
  quickBtn: {
    padding: '6px 12px',
    background: 'rgba(255,255,255,0.05)',
    border: '1px solid rgba(255,255,255,0.15)',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '12px',
    color: '#A1A1A1',
    transition: 'all 0.2s',
  },
  quickBtnActive: {
    background: '#9AE65C',
    borderColor: '#9AE65C',
    color: '#0A0A0A',
    fontWeight: 600,
  },
}

const WEEKDAYS = ['SU', 'MO', 'TU', 'WE', 'TH', 'FR', 'SA']
const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']

const QUICK_RANGES = [
  { label: 'Last 7 days', days: 7 },
  { label: 'Last 14 days', days: 14 },
  { label: 'Last 30 days', days: 30 },
  { label: 'Last 60 days', days: 60 },
  { label: 'Last 90 days', days: 90 },
]

export default function DateRangePicker({ startDate, endDate, onChange }: DateRangePickerProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [tempStart, setTempStart] = useState<Date | null>(startDate)
  const [tempEnd, setTempEnd] = useState<Date | null>(endDate)
  const [hoveredDate, setHoveredDate] = useState<Date | null>(null)
  const [viewDate, setViewDate] = useState(new Date(startDate.getFullYear(), startDate.getMonth(), 1))
  const dropdownRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false)
        setHoveredDate(null)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Reset temp state when opening
  useEffect(() => {
    if (isOpen) {
      setTempStart(startDate)
      setTempEnd(endDate)
    }
  }, [isOpen, startDate, endDate])

  const formatDate = (date: Date) => {
    return `${MONTHS[date.getMonth()].slice(0, 3)} ${date.getDate()}, ${date.getFullYear()}`
  }

  const getDaysInMonth = (year: number, month: number) => {
    return new Date(year, month + 1, 0).getDate()
  }

  const getFirstDayOfMonth = (year: number, month: number) => {
    return new Date(year, month, 1).getDay()
  }

  const isSameDay = (d1: Date, d2: Date) => {
    return d1.getFullYear() === d2.getFullYear() &&
           d1.getMonth() === d2.getMonth() &&
           d1.getDate() === d2.getDate()
  }

  // Check if date is in the selected/preview range
  const isInRange = (date: Date) => {
    if (!tempStart) return false

    // If we have both start and end, check if date is between them
    if (tempStart && tempEnd) {
      return date > tempStart && date < tempEnd
    }

    // If only start is selected and we're hovering, show preview range
    if (tempStart && !tempEnd && hoveredDate) {
      if (hoveredDate > tempStart) {
        return date > tempStart && date < hoveredDate
      } else if (hoveredDate < tempStart) {
        return date > hoveredDate && date < tempStart
      }
    }

    return false
  }

  // Handle day click - first click sets start, second click sets end
  const handleDayClick = (date: Date) => {
    if (!tempStart || (tempStart && tempEnd)) {
      // Start new selection
      setTempStart(date)
      setTempEnd(null)
    } else {
      // Complete the selection
      if (date < tempStart) {
        setTempEnd(tempStart)
        setTempStart(date)
      } else {
        setTempEnd(date)
      }
    }
  }

  const handleQuickSelect = (days: number) => {
    const end = new Date()
    const start = new Date()
    start.setDate(end.getDate() - days + 1)
    setTempStart(start)
    setTempEnd(end)
  }

  const handleDone = () => {
    if (tempStart && tempEnd) {
      onChange(tempStart, tempEnd)
      setIsOpen(false)
      setHoveredDate(null)
    }
  }

  const canDone = tempStart && tempEnd

  const handleClear = () => {
    const end = new Date()
    const start = new Date()
    start.setDate(end.getDate() - 6)
    setTempStart(start)
    setTempEnd(end)
  }

  const renderMonth = (monthOffset: number) => {
    const year = viewDate.getFullYear()
    const month = viewDate.getMonth() + monthOffset
    const actualDate = new Date(year, month, 1)
    const actualYear = actualDate.getFullYear()
    const actualMonth = actualDate.getMonth()
    const daysInMonth = getDaysInMonth(actualYear, actualMonth)
    const firstDay = getFirstDayOfMonth(actualYear, actualMonth)
    const today = new Date()

    const days = []
    for (let i = 0; i < firstDay; i++) {
      days.push(<div key={`empty-${i}`} style={{ ...styles.day, visibility: 'hidden' as const }}>-</div>)
    }

    for (let day = 1; day <= daysInMonth; day++) {
      const date = new Date(actualYear, actualMonth, day)
      const isStartDate = tempStart && isSameDay(date, tempStart)
      const isEndDate = tempEnd && isSameDay(date, tempEnd)
      const isSelected = isStartDate || isEndDate
      const inRange = isInRange(date)
      const isToday = isSameDay(date, today)
      const isFuture = date > today

      // Determine if this is a hovered end date (for preview)
      const isHoveredEnd = hoveredDate && isSameDay(date, hoveredDate) && tempStart && !tempEnd

      days.push(
        <button
          key={day}
          style={{
            ...styles.day,
            ...(isFuture ? styles.dayDisabled : {}),
            ...(inRange ? styles.dayInRange : {}),
            ...(isStartDate && (tempEnd || hoveredDate) ? styles.dayRangeStart : {}),
            ...(isEndDate || (isHoveredEnd && hoveredDate && tempStart && hoveredDate > tempStart) ? styles.dayRangeEnd : {}),
            ...(isSelected ? styles.daySelected : {}),
            ...(isHoveredEnd && !isSelected ? { ...styles.daySelected, opacity: 0.7 } : {}),
            ...(isToday && !isSelected ? styles.dayToday : {}),
          }}
          onClick={() => !isFuture && handleDayClick(date)}
          onMouseEnter={() => !isFuture && setHoveredDate(date)}
          disabled={isFuture}
        >
          {day}
        </button>
      )
    }

    return (
      <div style={styles.calendar} onMouseLeave={() => setHoveredDate(null)}>
        <div style={styles.monthTitle}>{MONTHS[actualMonth]} {actualYear}</div>
        <div style={styles.weekdays}>
          {WEEKDAYS.map(d => <div key={d} style={styles.weekday}>{d}</div>)}
        </div>
        <div style={styles.days}>{days}</div>
      </div>
    )
  }

  const daysDiff = Math.ceil((endDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24)) + 1

  return (
    <div style={styles.container} ref={dropdownRef}>
      <button style={styles.trigger} onClick={() => setIsOpen(!isOpen)}>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={styles.calendarIcon}>
          <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
          <line x1="16" y1="2" x2="16" y2="6"/>
          <line x1="8" y1="2" x2="8" y2="6"/>
          <line x1="3" y1="10" x2="21" y2="10"/>
        </svg>
        <span>{formatDate(startDate)} - {formatDate(endDate)}</span>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginLeft: 'auto' }}>
          <polyline points="6 9 12 15 18 9"/>
        </svg>
      </button>

      {isOpen && (
        <div style={styles.dropdown}>
          <div style={styles.header}>
            <button
              style={styles.navBtn}
              onClick={() => setViewDate(new Date(viewDate.getFullYear(), viewDate.getMonth() - 1, 1))}
            >
              ‹
            </button>
            <span style={styles.title}>Select Date Range</span>
            <button
              style={styles.navBtn}
              onClick={() => setViewDate(new Date(viewDate.getFullYear(), viewDate.getMonth() + 1, 1))}
            >
              ›
            </button>
          </div>

          <div style={styles.quickSelect}>
            {QUICK_RANGES.map(range => {
              const isActive = daysDiff === range.days
              return (
                <button
                  key={range.days}
                  style={{
                    ...styles.quickBtn,
                    ...(isActive ? styles.quickBtnActive : {}),
                  }}
                  onClick={() => handleQuickSelect(range.days)}
                >
                  {range.label}
                </button>
              )
            })}
          </div>

          <div style={styles.calendars}>
            {renderMonth(0)}
            {renderMonth(1)}
          </div>

          <div style={styles.footer}>
            <button
              style={styles.clearBtn}
              onClick={handleClear}
              onMouseOver={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.1)' }}
              onMouseOut={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.05)' }}
            >
              Clear
            </button>
            <button
              style={{
                ...styles.doneBtn,
                ...(!canDone ? styles.doneBtnDisabled : {}),
              }}
              onClick={handleDone}
              disabled={!canDone}
              onMouseOver={(e) => { if (canDone) e.currentTarget.style.background = '#8BD84E' }}
              onMouseOut={(e) => { if (canDone) e.currentTarget.style.background = '#9AE65C' }}
            >
              Done
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
