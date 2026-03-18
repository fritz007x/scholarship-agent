import { forwardRef } from 'react';

const Input = forwardRef(function Input(
  { label, error, type = 'text', optional = false, className = '', ...props },
  ref
) {
  return (
    <div className={className}>
      {label && (
        <label className="block text-sm font-medium text-gray-700 mb-1">
          {label}
          {optional && <span className="ml-1 text-xs font-normal text-gray-400">(optional)</span>}
        </label>
      )}
      <input
        ref={ref}
        type={type}
        className={`
          block w-full px-3 py-2 border rounded-md shadow-sm
          focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500
          ${error ? 'border-red-300' : 'border-gray-300'}
        `}
        {...props}
      />
      {error && (
        <p className="mt-1 text-sm text-red-600">{error}</p>
      )}
    </div>
  );
});

export default Input;
