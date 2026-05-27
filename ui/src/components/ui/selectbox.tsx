/*
 * SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
 * SPDX-License-Identifier: Apache-2.0
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
// NOTE: Component from https://github.com/shadcn-ui/ui/issues/927#issuecomment-2272458201
import { ArrowUpDownIcon, CheckIcon, XIcon } from "lucide-react";
import * as React from "react";

import { cn } from "@/lib/utils";

import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";

interface Option {
  value: string;
  key: string;
}

interface SelectBoxProps {
  options: Option[];
  value?: string[] | string;
  onChange?: (values: string[] | string) => void;
  placeholder?: string;
  inputPlaceholder?: string;
  emptyPlaceholder?: string;
  className?: string;
  multiple?: boolean;
  disabled?: boolean;
  searchable?: boolean;
}

const SelectBox = React.forwardRef<HTMLInputElement, SelectBoxProps>(
  (
    {
      inputPlaceholder,
      emptyPlaceholder,
      placeholder,
      className,
      options,
      value,
      onChange,
      multiple,
      disabled,
      searchable = true,
    },
    ref,
  ) => {
    const [searchTerm, setSearchTerm] = React.useState<string>("");
    const [isOpen, setIsOpen] = React.useState(false);

    const handleSelect = (selectedValue: string) => {
      if (multiple) {
        const newValue = Array.isArray(value)
          ? value.includes(selectedValue)
            ? value.filter((v) => v !== selectedValue) // Remove if exists
            : [...value, selectedValue] // Add if not exists
          : [selectedValue]; // If value is not an array, create a new array with selectedValue
        onChange?.(newValue);
      } else {
        onChange?.(selectedValue);
        setIsOpen(false);
      }
    };

    const handleClear = () => {
      onChange?.(multiple ? [] : "");
    };

    return (
      <Popover open={isOpen} onOpenChange={setIsOpen}>
        <PopoverTrigger asChild>
          <Button
            disabled={disabled}
            variant={"outline"}
            className={cn(
              "flex min-h-[36px] cursor-pointer items-center justify-between rounded-md border px-3 py-1 data-[state=open]:border-ring w-full h-full",
              className,
            )}
          >
            <div
              className={cn(
                "items-center gap-1 overflow-hidden text-sm",
                multiple
                  ? "flex flex-grow flex-wrap "
                  : "inline-flex whitespace-nowrap",
              )}
            >
              {value && value.length > 0 ? (
                multiple ? (
                  options
                    .filter(
                      (option) =>
                        Array.isArray(value) && value.includes(option.value),
                    )
                    ?.map((option) => (
                      <span
                        key={option.value}
                        className="inline-flex items-center gap-1 rounded-md border py-0.5 pl-2 pr-1 text-xs font-medium text-foreground transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                      >
                        <span>{option.key}</span>
                        <span
                          onClick={(e) => {
                            e.preventDefault();
                            handleSelect(option.value);
                          }}
                          className="flex items-center rounded-sm px-[1px] text-muted-foreground/60 hover:bg-accent hover:text-muted-foreground"
                        >
                          <XIcon />
                        </span>
                      </span>
                    ))
                ) : (
                  options.find((opt) => opt.value === value)?.key
                )
              ) : (
                <span className="mr-auto text-muted-foreground">
                  {placeholder}
                </span>
              )}
            </div>
            <div className="flex items-center self-stretch pl-1 text-muted-foreground/60 hover:text-foreground [&>div]:flex [&>div]:items-center [&>div]:self-stretch">
              {value && value.length > 0 ? (
                <div
                  onClick={(e) => {
                    e.preventDefault();
                    handleClear();
                  }}
                >
                  <XIcon className="size-4" />
                </div>
              ) : (
                <div>
                  <ArrowUpDownIcon className="size-4" />
                </div>
              )}
            </div>
          </Button>
        </PopoverTrigger>
        <PopoverContent
          className="w-[var(--radix-popover-trigger-width)] p-0"
          align="start"
        >
          <Command>
            {searchable ? (
              <div className="relative">
                <CommandInput
                  value={searchTerm}
                  onValueChange={(e) => setSearchTerm(e)}
                  ref={ref}
                  placeholder={inputPlaceholder ?? "Search..."}
                  className="h-9"
                />
                {searchTerm && (
                  <div
                    className="absolute inset-y-0 right-0 flex cursor-pointer items-center pr-3 text-muted-foreground hover:text-foreground"
                    onClick={() => setSearchTerm("")}
                  >
                    <XIcon className="size-4" />
                  </div>
                )}
              </div>
            ) : null}

            <CommandList>
              <CommandEmpty>
                {emptyPlaceholder ?? "No results found."}
              </CommandEmpty>
              <CommandGroup>
                <ScrollArea>
                  <div className="max-h-64">
                    {options?.map((option) => {
                      const isSelected =
                        Array.isArray(value) && value.includes(option.value);
                      return (
                        <CommandItem
                          key={option.value}
                          // value={option.value}
                          onSelect={() => handleSelect(option.value)}
                        >
                          {multiple && (
                            <div
                              className={cn(
                                "mr-2 flex h-4 w-4 items-center justify-center rounded-sm border border-primary",
                                isSelected
                                  ? "bg-primary text-primary-foreground"
                                  : "opacity-50 [&_svg]:invisible",
                              )}
                            >
                              <CheckIcon />
                            </div>
                          )}
                          <span>{option.key}</span>
                          {!multiple && option.value === value && (
                            <CheckIcon
                              className={cn(
                                "ml-auto",
                                option.value === value
                                  ? "opacity-100"
                                  : "opacity-0",
                              )}
                            />
                          )}
                        </CommandItem>
                      );
                    })}
                  </div>
                </ScrollArea>
              </CommandGroup>
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>
    );
  },
);

SelectBox.displayName = "SelectBox";

export { SelectBox };
