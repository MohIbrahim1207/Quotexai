import React, { useEffect, useState } from 'react';
import { Loader2, CheckCircle2, FileSearch, Brain, ShieldCheck, FileSpreadsheet } from 'lucide-react';

interface ProcessingStatusProps {
  currentStepIndex?: number;
}

const STEPS = [
  { label: 'Reading PDF document...', icon: FileSearch, desc: 'Extracting text streams and tabular blocks with PyMuPDF' },
  { label: 'Understanding quotation with Gemini AI...', icon: Brain, desc: 'Parsing line items, part numbers, and equipment groupings' },
  { label: 'Validating line items & arithmetic...', icon: ShieldCheck, desc: 'Cross-checking part numbers, unit prices, discounts, and totals' },
  { label: 'Preparing Excel template mapping...', icon: FileSpreadsheet, desc: 'Matching columns and preserving formulas & styles' },
];

export const ProcessingStatus: React.FC<ProcessingStatusProps> = () => {
  const [activeStep, setActiveStep] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setActiveStep((prev) => (prev < STEPS.length - 1 ? prev + 1 : prev));
    }, 1200);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="max-w-2xl mx-auto py-16 px-4">
      <div className="bg-white/75 border border-[#786446]/15 rounded-3xl p-8 shadow-xl backdrop-blur-xl">
        <div className="flex items-center space-x-4 mb-8 pb-6 border-b border-[#786446]/10">
          <div className="p-3 rounded-2xl bg-[#C98B4A]/10 text-[#C98B4A] ring-1 ring-[#C98B4A]/20 shadow-2xs">
            <Loader2 className="w-6 h-6 animate-spin" />
          </div>
          <div>
            <h3 className="text-xl font-bold text-[#26231F]">Analyzing Quotation</h3>
            <p className="text-xs text-[#716B61] mt-0.5">Processing document through extraction & validation pipeline...</p>
          </div>
        </div>

        <div className="space-y-6">
          {STEPS.map((step, idx) => {
            const isCompleted = idx < activeStep;
            const isCurrent = idx === activeStep;
            const StepIcon = step.icon;

            return (
              <div key={idx} className="flex items-start space-x-4">
                <div className="relative flex items-center justify-center">
                  <div
                    className={`w-10 h-10 rounded-2xl flex items-center justify-center transition-all duration-300 ${
                      isCompleted
                        ? 'bg-emerald-50 text-emerald-600 border border-emerald-200 shadow-2xs'
                        : isCurrent
                        ? 'bg-[#26231F] text-white shadow-md shadow-black/15 ring-2 ring-[#C98B4A]/40'
                        : 'bg-[#F5F1E8] text-[#716B61] border border-[#786446]/10'
                    }`}
                  >
                    {isCompleted ? <CheckCircle2 className="w-5 h-5" /> : <StepIcon className="w-4 h-4" />}
                  </div>
                  {idx < STEPS.length - 1 && (
                    <div
                      className={`absolute top-10 left-1/2 -translate-x-1/2 w-0.5 h-6 transition-colors duration-300 ${
                        isCompleted ? 'bg-emerald-300' : 'bg-[#786446]/15'
                      }`}
                    />
                  )}
                </div>

                <div className="pt-1">
                  <p
                    className={`text-sm font-semibold transition-colors ${
                      isCompleted ? 'text-[#26231F]' : isCurrent ? 'text-[#26231F]' : 'text-[#716B61]'
                    }`}
                  >
                    {step.label}
                  </p>
                  <p className="text-xs text-[#716B61] mt-0.5">{step.desc}</p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
