const fs = require('fs');

let content = fs.readFileSync('src/components/ApplicantPortal.tsx', 'utf8');
if (!content.includes('import { useGSAP }')) {
  content = content.replace(
    /import \{ Button \} from '\.\/ui\/Button';/g,
    `import { Button } from './ui/Button';\nimport { useGSAP } from '@gsap/react';\nimport { initScrollAnimations, initHoverEffects } from '../lib/animations';`
  );
  fs.writeFileSync('src/components/ApplicantPortal.tsx', content);
}
