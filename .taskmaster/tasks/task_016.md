# Task ID: 16

**Title:** Fix Astro Starlight Documentation Site Content Discovery Issue

**Status:** done

**Dependencies:** None

**Priority:** medium

**Description:** Resolve the docsLoader content discovery bug where markdown files in subdirectories (getting-started/, setup/, guides/, reference/) are not being detected, with only index.mdx being discovered. Ensure all 9 documentation pages build and deploy correctly to jambot.app via GitHub Actions.

**Details:**

ROOT CAUSE INVESTIGATION:
The docsLoader is failing to discover markdown files in subdirectories, suggesting a configuration issue in content.config.ts or a Starlight version compatibility problem.

IMPLEMENTATION STEPS:

1. **Verify Directory Structure and File Permissions:**
   - Confirm all subdirectories exist: getting-started/, setup/, guides/, reference/
   - Check file permissions on all .md/.mdx files (should be readable)
   - Verify file naming conventions match Starlight expectations
   - List all 9 expected documentation pages and their paths

2. **Audit content.config.ts Configuration:**
   - Review the docsLoader configuration in content.config.ts
   - Check glob patterns used for content discovery (should include subdirectories like `**/*.{md,mdx}`)
   - Verify the base path configuration points to correct docs directory
   - Ensure collections are properly defined for each subdirectory
   - Example correct configuration:
   ```typescript
   import { defineCollection } from 'astro:content';
   import { docsLoader } from '@astrojs/starlight/loaders';
   
   export const collections = {
     docs: defineCollection({
       loader: docsLoader({
         base: './src/content/docs',
         // Ensure pattern includes subdirectories
         pattern: '**/*.{md,mdx}'
       })
     })
   };
   ```

3. **Check Starlight Version Compatibility:**
   - Review package.json for @astrojs/starlight version
   - Check Astro version compatibility with Starlight
   - Review Starlight changelog for breaking changes in docsLoader API
   - Update to latest stable versions if needed
   - Run `npm install` or `pnpm install` to ensure dependencies are properly installed

4. **Verify Astro Configuration:**
   - Check astro.config.mjs for Starlight integration setup
   - Ensure sidebar configuration references all subdirectories
   - Example sidebar config:
   ```javascript
   starlight({
     sidebar: [
       { label: 'Getting Started', autogenerate: { directory: 'getting-started' } },
       { label: 'Setup', autogenerate: { directory: 'setup' } },
       { label: 'Guides', autogenerate: { directory: 'guides' } },
       { label: 'Reference', autogenerate: { directory: 'reference' } }
     ]
   })
   ```

5. **Build and Deployment Verification:**
   - Test local build with `npm run build` or `pnpm build`
   - Verify all 9 pages are generated in dist/ directory
   - Check build logs for warnings or errors about missing content
   - Review GitHub Actions workflow file (.github/workflows/*.yml)
   - Ensure deployment step correctly uploads all built files
   - Verify jambot.app domain configuration and DNS settings

6. **Add Logging and Debugging:**
   - Add console.log statements in content.config.ts to debug loader behavior
   - Use Astro's --verbose flag during build to see detailed output
   - Check if files are being excluded by .gitignore or .astroignore

7. **Common Fixes:**
   - Ensure no trailing slashes in path configurations
   - Check for case sensitivity issues in file/directory names
   - Verify no special characters in filenames that might break glob patterns
   - Clear Astro cache: `rm -rf .astro` and rebuild

**Test Strategy:**

1. **Local Content Discovery Test:**
   - Run `npm run dev` or `pnpm dev` locally
   - Navigate to each subdirectory route in browser
   - Verify all 9 documentation pages are accessible
   - Check browser console and terminal for errors

2. **Build Verification:**
   - Run `npm run build` or `pnpm build`
   - Inspect dist/ directory structure
   - Count generated HTML files (should match 9+ pages including index)
   - Verify subdirectory structure is preserved in output

3. **Content Discovery Audit:**
   - Add a test script to list all discovered content files
   - Verify docsLoader finds files in all subdirectories:
     - getting-started/
     - setup/
     - guides/
     - reference/
   - Confirm index.mdx plus all subdirectory files are included

4. **GitHub Actions Deployment Test:**
   - Push changes to repository
   - Monitor GitHub Actions workflow execution
   - Check build logs for successful completion
   - Verify no warnings about missing content files
   - Confirm deployment step completes without errors

5. **Production Verification:**
   - Visit jambot.app after deployment
   - Navigate to each documentation section
   - Verify all 9 pages load correctly
   - Check navigation/sidebar shows all sections
   - Test internal links between documentation pages
   - Verify no 404 errors for any documentation routes

6. **Regression Testing:**
   - Add a new test markdown file in one of the subdirectories
   - Rebuild and verify it's discovered
   - Remove test file to confirm cleanup works
