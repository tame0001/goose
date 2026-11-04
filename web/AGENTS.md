# Angular Frontend Rules (goose/web)

## Architecture & Stack
- **Framework**: Angular 22 (Standalone components only, Angular Signals, Vitest).
- **UI Components**: Angular Material (Material 3) with `@angular/cdk`.
- **Styling**: SCSS (Dart Sass). Tailwind CSS is **NOT** used in this project.
  - Global styles and layout helpers are in `src/styles.scss`.
  - Responsive breakpoint mixins are in `src/_mixins.scss`.
  - Material 3 theme configuration is in `src/material-theme.scss`.

## Coding Guidelines
- **Standalone Only**: Never generate `NgModule`. All components, directives, and pipes must be standalone.
- **Reactivity**: Prefer Signals (`signal`, `computed`, `linkedSignal`) over manual RxJS subscriptions.
- **Dependency Injection**: Always use `inject(Service)` instead of constructor parameter injection.
- **Control Flow**: Use modern template syntax (`@if`, `@for`, `@switch`). Never use `*ngIf` or `*ngFor`.
- **Inputs & Outputs**: Use signal inputs (`input()`, `input.required()`) and `output()`, not `@Input()` / `@Output()` decorators.
- **Styling Conventions**:
  - Write scoped SCSS in component `.scss` files.
  - Use responsive mixins (`@include mobile`, `@include tablet`, `@include desktop`) from `src/_mixins.scss`.
  - Use `.table-scroll-container` to wrap wide financial data tables (`mat-table`) for smooth mobile horizontal scrolling.
  - Avoid creating custom dropdowns or modals from scratch; use Angular Material's built-in components (`MatDialog`, `MatSelect`, `MatTable`, etc.).

## Verification Commands
- Build: `npm --prefix web run build`
- Test: `npm --prefix web test`
