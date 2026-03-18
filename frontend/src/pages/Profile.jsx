import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { profileAPI } from '../services/api';
import Layout from '../components/layout/Layout';
import Card from '../components/common/Card';
import Button from '../components/common/Button';
import Input from '../components/common/Input';
import { Save, ChevronDown, ChevronUp } from 'lucide-react';

function FormSection({ title, children, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="border rounded-lg">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between p-4 text-left font-medium"
      >
        {title}
        {open ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
      </button>
      {open && <div className="p-4 pt-0 space-y-4">{children}</div>}
    </div>
  );
}

export default function Profile() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });

  const { register, handleSubmit, reset } = useForm();

  useEffect(() => {
    loadProfile();
  }, []);

  const loadProfile = async () => {
    try {
      const response = await profileAPI.get();
      reset(response.data);
    } catch (err) {
      console.error('Failed to load profile', err);
    } finally {
      setLoading(false);
    }
  };

  const onSubmit = async (data) => {
    setSaving(true);
    setMessage({ type: '', text: '' });

    try {
      // Strip read-only fields that came from the GET response
      const { id, user_id, created_at, updated_at, ...profileData } = data;

      // Convert empty strings to null and numeric strings to numbers
      const cleaned = Object.fromEntries(
        Object.entries(profileData).map(([key, value]) => {
          if (value === '' || value === undefined) return [key, null];
          if (['gpa', 'gpa_scale', 'graduation_year', 'class_rank', 'class_size', 'estimated_efc'].includes(key) && value !== null) {
            const num = Number(value);
            return [key, isNaN(num) ? null : num];
          }
          return [key, value];
        })
      );

      await profileAPI.update(cleaned);
      setMessage({ type: 'success', text: 'Profile saved successfully' });
    } catch (err) {
      setMessage({ type: 'error', text: err.response?.data?.detail || 'Failed to save profile' });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="max-w-3xl mx-auto space-y-6">
        <div className="flex justify-between items-center">
          <h1 className="text-2xl font-bold text-gray-900">Profile</h1>
        </div>

        {message.text && (
          <div
            className={`p-4 rounded-md ${
              message.type === 'success' ? 'bg-green-50 text-green-600' : 'bg-red-50 text-red-600'
            }`}
          >
            {message.text}
          </div>
        )}

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <Card>
            <FormSection title="Personal Information" defaultOpen={true}>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Input label="First Name" {...register('first_name')} />
                <Input label="Middle Name" {...register('middle_name')} />
                <Input label="Last Name" {...register('last_name')} />
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Input label="Date of Birth" type="date" {...register('date_of_birth')} />
                <Input label="Phone" type="tel" {...register('phone')} />
              </div>
              <Input label="Street Address" {...register('street_address')} />
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Input label="City" {...register('city')} />
                <Input label="State" {...register('state')} />
                <Input label="ZIP Code" {...register('zip_code')} />
                <Input label="Country" {...register('country')} />
              </div>
            </FormSection>
          </Card>

          <Card>
            <FormSection title="Academic Information">
              <Input label="Current School" {...register('current_school')} />
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Input label="Graduation Year" type="number" {...register('graduation_year')} />
                <div className="grid grid-cols-2 gap-4">
                  <Input label="GPA" type="number" step="0.01" {...register('gpa')} />
                  <Input label="GPA Scale" type="number" step="0.1" {...register('gpa_scale')} />
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Input label="Class Rank" type="number" optional {...register('class_rank')} />
                <Input label="Class Size" type="number" optional {...register('class_size')} />
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Input label="Intended Major" {...register('intended_major')} />
                <Input label="Intended Minor" optional {...register('intended_minor')} />
              </div>
            </FormSection>
          </Card>

          <Card>
            <FormSection title="Demographics (Optional)">
              <p className="text-sm text-gray-500 mb-4">
                This information is optional and can help match you with scholarships.
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Gender</label>
                  <select
                    {...register('gender')}
                    className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="">Prefer not to say</option>
                    <option value="male">Male</option>
                    <option value="female">Female</option>
                    <option value="non_binary">Non-binary</option>
                    <option value="other">Other</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Citizenship / Immigration Status
                  </label>
                  <select
                    {...register('citizenship_status')}
                    className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="">Select...</option>
                    <optgroup label="US Status">
                      <option value="us_citizen">US Citizen</option>
                      <option value="us_national">US National</option>
                      <option value="permanent_resident">Permanent Resident (Green Card)</option>
                      <option value="daca">DACA Recipient</option>
                      <option value="refugee_asylee">Refugee / Asylee</option>
                    </optgroup>
                    <optgroup label="Visa Holders">
                      <option value="f1_visa">F-1 Student Visa</option>
                      <option value="j1_visa">J-1 Exchange Visitor</option>
                      <option value="h1b_visa">H-1B Work Visa</option>
                      <option value="h4_visa">H-4 Dependent Visa</option>
                      <option value="l1_visa">L-1 Intracompany Transfer</option>
                      <option value="other_visa">Other Visa Type</option>
                    </optgroup>
                    <optgroup label="Other">
                      <option value="undocumented">Undocumented</option>
                      <option value="pending_status">Pending Immigration Status</option>
                      <option value="non_us_resident">Non-US Resident (Outside US)</option>
                      <option value="other">Other</option>
                    </optgroup>
                  </select>
                </div>
              </div>
              <div className="flex items-center">
                <input
                  type="checkbox"
                  id="first_gen"
                  {...register('first_generation')}
                  className="h-4 w-4 text-indigo-600 rounded"
                />
                <label htmlFor="first_gen" className="ml-2 text-sm text-gray-700">
                  First generation college student
                </label>
              </div>
            </FormSection>
          </Card>

          <Card>
            <FormSection title="Financial Information (Optional)">
              <p className="text-sm text-gray-500 mb-4">
                This information helps match you with need-based scholarships.
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Input
                  label="Estimated EFC"
                  type="number"
                  placeholder="Expected Family Contribution"
                  {...register('estimated_efc')}
                />
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Household Income Range
                  </label>
                  <select
                    {...register('household_income_range')}
                    className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="">Prefer not to say</option>
                    <option value="0-30000">$0 - $30,000</option>
                    <option value="30000-60000">$30,000 - $60,000</option>
                    <option value="60000-100000">$60,000 - $100,000</option>
                    <option value="100000-150000">$100,000 - $150,000</option>
                    <option value="150000+">$150,000+</option>
                  </select>
                </div>
              </div>
            </FormSection>
          </Card>

          <div className="flex justify-end">
            <Button type="submit" loading={saving}>
              <Save className="w-4 h-4 mr-2" />
              Save Profile
            </Button>
          </div>
        </form>
      </div>
    </Layout>
  );
}
