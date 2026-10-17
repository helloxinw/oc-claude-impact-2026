import * as React from 'react'
import { cn } from '@/lib/utils'
function Input({ className, type = 'text', ...props }: React.ComponentProps<'input'>) {
  return <input data-slot="input" type={type} className={cn('flex h-10 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-xs outline-none transition-colors placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/20 disabled:cursor-not-allowed disabled:opacity-50', className)} {...props} />
}
export { Input }
