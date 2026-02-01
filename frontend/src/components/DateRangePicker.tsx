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
    background: '#FFFFFF',
    borderRadius: '12px',
    boxShadow: '0 10px 40px rgba(0,0,0,0.3)',
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
    color: '#333',
    fontSize: '18px',
  },
  title: {
    fontSize: '16px',
    fontWeight: 600,
    color: '#333',
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
    color: '#333',
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
    color: '#999',
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
    borderRadius: '4px',
    cursor: 'pointer',
    border: 'none',
    background: 'transparent',
    color: '#333',
  },
  dayDisabled: {
    color: '#ccc',
    cursor: 'default',
  },
  daySelected: {
    background: '#4A7DFF',
    color: '#FFFFFF',
  },
  dayInRange: {
    background: '#E8F0FF',
    color: '#333',
  },
  dayToday: {
    border: '1px solid #4A7DFF',
  },
  footer: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: '16px',
    paddingTop: '16px',
    borderTop: '1px solid #eee',
  },
  clearBtn: {
    padding: '8px 16px',
    background: '#f5f5f5',
    border: '1px solid #ddd',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '14px',
    color: '#333',
  },
  doneBtn: {
    padding: '8px 20px',
    background: '#4A7DFF',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '14px',
    color: '#FFFFFF',
    fontWeight: 500,
  },
  quickSelect: {
    display: 'flex',
    gap: '8px',
    marginBottom: '16px',
    flexWrap: 'wrap' as const,
  },
  quickBtn: {
    padding: '6px 12px',
    background: '#f5f5f5',
    border: '1px solid #ddd',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '12px',
    color: '#666',
  },
  quickBtnActive: {
    background: '#4A7DFF',
    borderColor: '#4A7DFF',
    color: '#FFFFFF',
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
  const [tempStart, setTempStart] = useState(startDate)
  const [tempEnd, setTempEnd] = useState(endDate)
  const [viewDate, setViewDate] = useState(new Date(startDate.getFullYear(), startDate.getMonth(), 1))
  const dropdownRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

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

  const isInRange = (date: Date) => {
    return date > tempStart && date < tempEnd
  }

  const handleDayClick = (date: Date) => {
    if (!tempStart || (tempStart && tempEnd)) {
      setTempStart(date)
      setTempEnd(date)
    } else {
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
    onChange(tempStart, tempEnd)
    setIsOpen(false)
  }

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
      const isSelected = isSameDay(date, tempStart) || isSameDay(date, tempEnd)
      const inRange = isInRange(date)
      const isToday = isSameDay(date, today)
      const isFuture = date > today

      days.push(
        <button
          key={day}
          style={{
            ...styles.day,
            ...(isFuture ? styles.dayDisabled : {}),
            ...(inRange ? styles.dayInRange : {}),
            ...(isSelected ? styles.daySelected : {}),
            ...(isToday && !isSelected ? styles.dayToday : {}),
          }}
          onClick={() => !isFuture && handleDayClick(date)}
          disabled={isFuture}
        >
          {day}
        </button>
      )
    }

    return (
      <div style={styles.calendar}>
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
            <button style={styles.clearBtn} onClick={handleClear}>Clear</button>
            <button style={styles.doneBtn} onClick={handleDone}>Done</button>
          </div>
        </div>
      )}
    </div>
  )
}
