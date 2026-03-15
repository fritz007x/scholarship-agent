import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import Card from './Card';

describe('Card', () => {
  it('renders children', () => {
    render(<Card>Card content</Card>);
    expect(screen.getByText('Card content')).toBeInTheDocument();
  });

  it('applies default styling', () => {
    render(<Card>Test</Card>);
    const card = screen.getByText('Test').closest('div');
    expect(card.className).toContain('bg-white');
    expect(card.className).toContain('rounded-lg');
    expect(card.className).toContain('shadow');
  });

  it('appends custom className', () => {
    render(<Card className="extra-class">Test</Card>);
    const card = screen.getByText('Test').closest('div');
    expect(card.className).toContain('extra-class');
  });

  it('passes through additional props', () => {
    render(<Card data-testid="my-card">Test</Card>);
    expect(screen.getByTestId('my-card')).toBeInTheDocument();
  });
});
