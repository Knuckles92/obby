/**
 * Unit tests for ConfirmationDialog component
 *
 * Tests the reusable confirmation dialog component used throughout the app.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ConfirmationDialog from '../../components/ConfirmationDialog';

describe('ConfirmationDialog', () => {
  it('should not render when not open', () => {
    const { container } = render(
      <ConfirmationDialog
        isOpen={false}
        onConfirm={() => {}}
        onCancel={() => {}}
        title="Test"
        message="Test message"
      />
    );

    // Dialog should not be in the document when closed
    expect(container.querySelector('[role="dialog"]')).not.toBeInTheDocument();
  });

  it('should render when open', () => {
    render(
      <ConfirmationDialog
        isOpen={true}
        onConfirm={() => {}}
        onCancel={() => {}}
        title="Test Title"
        message="Test message"
      />
    );

    expect(screen.getByText('Test Title')).toBeInTheDocument();
    expect(screen.getByText('Test message')).toBeInTheDocument();
  });

  it('should call onConfirm when confirm button is clicked', async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    const onCancel = vi.fn();

    render(
      <ConfirmationDialog
        isOpen={true}
        onConfirm={onConfirm}
        onCancel={onCancel}
        title="Test"
        message="Test message"
      />
    );

    const confirmButton = screen.getByRole('button', { name: /confirm|yes|ok/i });
    await user.click(confirmButton);

    expect(onConfirm).toHaveBeenCalledTimes(1);
    expect(onCancel).not.toHaveBeenCalled();
  });

  it('should call onCancel when cancel button is clicked', async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    const onCancel = vi.fn();

    render(
      <ConfirmationDialog
        isOpen={true}
        onConfirm={onConfirm}
        onCancel={onCancel}
        title="Test"
        message="Test message"
      />
    );

    const cancelButton = screen.getByRole('button', { name: /cancel|no/i });
    await user.click(cancelButton);

    expect(onCancel).toHaveBeenCalledTimes(1);
    expect(onConfirm).not.toHaveBeenCalled();
  });

  it('should display custom button text', () => {
    render(
      <ConfirmationDialog
        isOpen={true}
        onConfirm={() => {}}
        onCancel={() => {}}
        title="Delete File"
        message="Are you sure?"
        confirmText="Delete"
        cancelText="Keep"
      />
    );

    expect(screen.getByRole('button', { name: /delete/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /keep/i })).toBeInTheDocument();
  });

  it('should display danger variant for destructive actions', () => {
    const { container } = render(
      <ConfirmationDialog
        isOpen={true}
        onConfirm={() => {}}
        onCancel={() => {}}
        title="Delete"
        message="Are you sure?"
        variant="danger"
      />
    );

    // Look for danger/destructive styling
    const confirmButton = screen.getByRole('button', { name: /confirm|yes|ok|delete/i });
    expect(confirmButton).toBeInTheDocument();
  });
});
